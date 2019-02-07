########
# Copyright (c) 2016-2019 Cloudify Platform Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pycdlib
import os
import re
from io import BytesIO

from cloudify import ctx

# This package imports
from cloudify_vsphere.utils import op
from vsphere_plugin_common import (
    with_rawvolume_client,
)


def _joliet_name(name):
    if name[0] == "/":
        name = name[1:]
    return "/{}".format(name[:64])


def _name_cleanup(name):
    return re.sub('[^A-Z0-9_]{1}', r'_', name.upper())


def _iso_name(name):
    if name[0] == "/":
        name = name[1:]

    name_splited = name.split('.')
    if len(name_splited[-1]) <= 3 and len(name_splited) > 1:
        return "/{}.{};1".format(
            _name_cleanup("_".join(name_splited[:-1])[:8]),
            _name_cleanup(name_splited[-1]))
    else:
        return "/{}.;1".format(_name_cleanup(name[:8]))


@op
@with_rawvolume_client
def create(rawvolume_client, files, **kwargs):
    ctx.logger.info("Creating new iso image.")

    iso = pycdlib.PyCdlib()
    iso.new(vol_ident='cidata', joliet=3, rock_ridge='1.09')

    if not files:
        files = ctx.node.properties.get('files', {})

    for name in files:
        file_bufer = BytesIO()
        file_bufer.write(files[name].encode())
        iso.add_fp(file_bufer, len(files[name]),
                   _iso_name(name), rr_name=name,
                   joliet_path=_joliet_name(name))

    outiso = BytesIO()
    iso.write_fp(outiso)
    outiso.seek(0, os.SEEK_END)
    iso_size = outiso.tell()
    iso.close()
    outiso.seek(0, os.SEEK_SET)

    ctx.logger.info("ISO size: {}".format(repr(iso_size)))

    rawvolume_client.upload_file(
        allowed_datacenters=["Datacenter"],
        allowed_datastores=["datastore1"],
        remote_file="/cloudinit/cloud_init.iso",
        data=outiso,
        host=ctx.node.properties['connection_config']['host'],
        port=ctx.node.properties['connection_config']['port'])
