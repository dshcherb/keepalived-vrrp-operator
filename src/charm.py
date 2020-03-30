#!/usr/bin/env python3

import subprocess
import logging
import sys

sys.path.append('lib') # noqa

from ops.framework import (
    EventBase,
    EventsBase,
    CharmBase,
    StoredState,
)

from ops.main import main
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from peers import KeepalivedPeers
from interface_vrrp_parameters import VRRPParametersRequires

logger = logging.getLogger(__name__)


class KeepalivedInitializedEvent(EventBase):
    pass


class KeepalivedEvents(EventsBase):
    pass


class KeepalivedCharm(CharmBase):

    on = KeepalivedEvents()
    state = StoredState()

    def __init__(self, *args):
        super().__init__(*args)

        self.keepalived_conf_file = Path(f'/etc/keepalived/juju-{self.app.name}.cfg')

        self.framework.observe(self.on.install, self.on_install)
        self.peers = KeepalivedPeers(self, 'keepalived-peers')
        self.primary = VRRPParametersRequires(self, 'vrrp-parameters')

    def on_install(self, event):
        subprocess.check_call(['apt', 'update'])
        subprocess.check_call(['apt', 'install', '-yq', 'keepalived'])
        self.on.keepalived_initialized.emit()

    def on_primary_changed(self, event):
        self.update_config()

    def update_config(self):
        ctxt = {
            'is_initial': self.peers.initial_unit == self.model.unit.name,
            'vrrp_instances': self.primary.vrrp_instances
        }
        env = Environment(loader=FileSystemLoader('templates'))
        template = env.get_template('keepalived.conf.j2')
        rendered_content = template.render(ctxt)
        self.haproxy_conf_file.write_text(rendered_content)

        subprocess.check_call(['systemctl', 'restart', 'keepalived'])


if __name__ == '__main__':
    main(KeepalivedCharm)
