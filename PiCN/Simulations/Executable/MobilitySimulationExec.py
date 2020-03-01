"""Mobility Simulation executable"""

import logging
import argparse

from PiCN.Logger import Logger
from PiCN.Packets import Name
from PiCN.Simulations.MobilitySimulations.Model.StationaryNode import StationaryNode
from PiCN.Simulations.MobilitySimulations.Model.MobileNode import MobileNode

from PiCN.Simulations.MobilitySimulations.MobilitySimulation import MobilitySimulation


def main(argv):

    # Log Level
    if args.logging == 'error':
        log_level = logging.ERROR
    elif args.logging == 'warning':
        log_level = logging.WARNING
    elif args.logging == 'info':
        log_level = logging.INFO
    elif args.logging == 'debug':
        log_level = logging.DEBUG
    else:
        log_level = 255
    logger = Logger("MobilitySimulation", log_level)

    # Info
    logger.info("Mobility Simulation config params...")
    logger.info("#run:           " + str(args.run))
    logger.info("#mobiles:       " + str(args.mobiles))
    logger.info("#stations:      " + str(args.stations))
    logger.info("Log Level:      " + args.logging)
    logger.info("Optimizer:      " + str(args.optimizer))

    # create a list of mobile nodes
    named_functions = {"/rsu/func/f1": "PYTHON\nf\ndef f(a, b, c):\n return a+b+c",
                       "/rsu/func/f2": "PYTHON\nf\ndef f(a, b, c):\n return a*b*c",
                       "/rsu/func/f3": "PYTHON\nf\ndef f(a, b, c):\n return a-b-c",
                       "/rsu/func/f4": "PYTHON\nf\ndef f(a, b, c):\n return a**b**c",
                       "/rsu/func/f5": "PYTHON\nf\ndef f(a, b, c):\n return a/b/c"}
    function_names = [
        Name("/rsu/func/f1_(1,2,3)NFN"),
        Name("/rsu/func/f2_(1,2,3)NFN"),
        Name("/rsu/func/f3_(1,2,3)NFN"),
        Name("/rsu/func/f4_(1,2,3)NFN"),
        Name("/rsu/func/f5_(1,2,3)NFN")
    ]

    # create instances of stationary nodes
    stationary_nodes_list = []
    for i in range(0, args.stations):
        stationary_nodes_list.append(StationaryNode(node_id=i, com_range=0.5))

    # create instances of mobile nodes
    mobile_nodes_list = []
    for i in range(0, args.mobiles):
        mobile_nodes_list.append(MobileNode(node_id=i, spawn_point=0, speed=60, direction=1))

    simulation = None
    if args.optimizer == "Edge":
        simulation = MobilitySimulation(run_id=args.run, mobile_nodes=mobile_nodes_list,
                                        stationary_nodes=stationary_nodes_list, stationary_node_distance=0.5,
                                        named_functions=named_functions, function_names=function_names,
                                        forwarder="NFNForwarder", optimizer="EdgeComputingOptimizer",
                                        use_distribution_helper=True)

    else:
        simulation = MobilitySimulation(run_id=args.run, mobile_nodes=mobile_nodes_list,
                                        stationary_nodes=stationary_nodes_list, stationary_node_distance=0.5,
                                        named_functions=named_functions, function_names=function_names,
                                        forwarder="NFNForwarder", optimizer="ToDataFirstOptimizer",
                                        use_distribution_helper=True)

    simulation.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MobilitySimulation')
    parser.add_argument('-r', '--run', type=int, default=1, help="The run number of the simulation")
    parser.add_argument('-m', '--mobiles', type=int, default=5, help="The number of mobile nodes to consider")
    parser.add_argument('-s', '--stations', type=int, default=2, help="The number of stationary nodes to consider")
    parser.add_argument('-l', '--logging', choices=['debug', 'info', 'warning', 'error', 'none'], type=str, default='info', help='Logging Level (default: info)')
    parser.add_argument('-e', '--optimizer', choices=['ToDataFirst', 'Edge'], type=str, default="ToDataFirst", help="Choose the NFN Optimizer")
    args = parser.parse_args()
    main(args)
