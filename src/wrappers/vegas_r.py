#!/usr/bin/env python

'''Vegas-style single-threshold congestion avoidance (VegasR) on the authors'
genericCC/CCmatic sender (third_party/ccmatic_genericCC). Separate from the
built-in kernel `vegas` scheme.

The queue target R (packets) is required: set the VEGAS_R environment
variable, or `R` under `vegas_r` in src/config.yml. It must be positive.
'''

import os
import sys
from math import isinf, isnan
from os import path
from subprocess import check_call

import arg_parser
import context
from helpers import utils


def get_r():
    r = os.environ.get('VEGAS_R')
    if r is None:
        r = utils.parse_config()['schemes']['vegas_r'].get('R')
    try:
        r = float(r)
    except (TypeError, ValueError):
        r = None
    if r is None or isnan(r) or isinf(r) or r <= 0:
        sys.exit('vegas_r: set VEGAS_R (or R in src/config.yml) to a '
                 'positive number of packets')
    return r


def main():
    args = arg_parser.receiver_first()

    cc_repo = path.join(context.third_party_dir, 'ccmatic_genericCC')
    recv_src = path.join(cc_repo, 'receiver')
    send_src = path.join(cc_repo, 'sender')

    if args.option == 'deps':
        print ('makepp libboost-dev libprotobuf-dev protobuf-c-compiler '
               'protobuf-compiler libjemalloc-dev')
        return

    if args.option == 'setup':
        # the patch also adds the ccmatic policies (shared sender)
        utils.apply_patch('ccmatic.patch', cc_repo)
        check_call(['makepp'], cwd=cc_repo)
        return

    if args.option == 'receiver':
        check_call([recv_src, args.port])
        return

    if args.option == 'sender':
        sh_cmd = (
            '%s serverip=%s serverport=%s offduration=1 '
            'onduration=1000000 traffic_params=deterministic,num_cycles=1 '
            'cctype=vegas_r r_target=%r'
            % (send_src, args.ip, args.port, get_r()))

        with open(os.devnull, 'w') as devnull:
            # suppress debugging output to stdout
            check_call(sh_cmd, shell=True, stdout=devnull)
        return


if __name__ == '__main__':
    main()
