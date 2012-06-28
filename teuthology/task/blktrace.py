from cStringIO import StringIO

import contextlib
import logging
import os
import re
import yaml

from teuthology import misc as teuthology
from teuthology import contextutil
from ..orchestra import run 

log = logging.getLogger(__name__)
blktrace = '/usr/sbin/blktrace'
log_dir = '/tmp/cephtest/archive/performance/blktrace'

@contextlib.contextmanager
def setup(ctx, config):
    osds = ctx.cluster.only(teuthology.is_type('osd'))
    for remote, roles_for_host in osds.remotes.iteritems():
        log.info('Creating %s on %s' % (log_dir,remote.name))
        proc = remote.run(
            args=['mkdir', '-p', '-m0755', '--', log_dir],
            wait=False,
            )
    yield

@contextlib.contextmanager
def execute(ctx, config):
    osds = ctx.cluster.only(teuthology.is_type('osd'))
    for remote, roles_for_host in osds.remotes.iteritems():
        roles_to_devs = ctx.disk_config.remote_to_roles_to_dev[remote]
        roles_to_journals = ctx.disk_config.remote_to_roles_to_journals[remote]
        for id_ in teuthology.roles_of_type(roles_for_host, 'osd'):
            if roles_to_devs.get(id_):
                dev = roles_to_devs[id_]
                log.info("running blktrace on %s: %s" % (remote.name, dev))
                proc = remote.run(
                    args=[
                        'cd',
                        log_dir,
                        run.Raw(';'),
                        'sudo',
                        blktrace,
                        '-o',
                        dev.rsplit("/", 1)[1],
                        '-d',
                        dev,
                        ],
                    wait=False,   
                    )
#    nodes = {}
#    for client, properties in config.iteritems():
#        if properties is None:
#            properties = {}
#        gen_movies = properties.get('gen_movies', 'false')
#
#        cluster = ctx.cluster.only(client)
#        for remote in cluster.remotes.iterkeys():
#            proc = remote.run(
#                args=[
#                    os.path.join(bin_dir, 'blktrace'),
#                    '-t',
#                    log_dir,
#                    '-o'
#                    '%s/%s' % (logdir, device),
#                    '-F10',
#                    ],
#                wait=False,        
#                )
#            nodes[remote] = proc
    try:
        yield
    finally:
        osds = ctx.cluster.only(teuthology.is_type('osd'))
        for remote, roles_for_host in osds.remotes.iteritems():
            log.info('stopping all blktrace processes on %s' % (remote.name))
            remote.run(args=['sudo', 'pkill', '-f', 'blktrace'])

@contextlib.contextmanager
def task(ctx, config):
    if config is None:
        config = dict(('client.{id}'.format(id=id_), None)
                  for id_ in teuthology.all_roles_of_type(ctx.cluster, 'client'))
    elif isinstance(config, list):
        config = dict.fromkeys(config)

    with contextutil.nested(
        lambda: setup(ctx=ctx, config=config),
        lambda: execute(ctx=ctx, config=config),
        ):
        yield

