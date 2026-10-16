#!/usr/bin/env python

'''Shared implementation of the CCmatic (NSDI'24) Listing 2 policies.

Backed by the authors' genericCC fork (third_party/ccmatic_genericCC); the
per-scheme wrappers (cc_qdel.py, ...) just call main() with a policy name.
'''

import os
from os import path
from subprocess import check_call

import arg_parser
import context
from helpers import utils

POLICIES = ['cc_qdel', 'cc_probe_fast', 'cc_probe_drain', 'cc_probe_slow',
            'cc_probe_qdel']


def main(policy):
    assert policy in POLICIES
    args = arg_parser.receiver_first()

    cc_repo = path.join(context.third_party_dir, 'ccmatic_genericCC')
    recv_src = path.join(cc_repo, 'receiver')
    send_src = path.join(cc_repo, 'sender')

    if args.option == 'deps':
        print ('makepp libboost-dev libprotobuf-dev protobuf-c-compiler '
               'protobuf-compiler libjemalloc-dev')
        return

    if args.option == 'setup':
        # adds the CcmaticPolicy class and the 'cctype=ccmatic policy=NAME'
        # sender option
        utils.apply_patch('ccmatic.patch', cc_repo)
        check_call(['makepp'], cwd=cc_repo)
        return

    if args.option == 'receiver':
        cmd = [recv_src, args.port]
        check_call(cmd)
        return

    if args.option == 'sender':
        sh_cmd = (
            '%s serverip=%s serverport=%s offduration=1 '
            'onduration=1000000 traffic_params=deterministic,num_cycles=1 '
            'cctype=ccmatic policy=%s'
            % (send_src, args.ip, args.port, policy))

        with open(os.devnull, 'w') as devnull:
            # suppress debugging output to stdout
            check_call(sh_cmd, shell=True, stdout=devnull)
        return
