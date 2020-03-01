"""Distribution Helper for creating function names requested by consuming nodes following a ZipfMandelbrot
distribution. Content of this class is inspired by the ConsumerZipfMandelbrot implementation presented in the ndnSIM
project: https://ndnsim.net/current/doxygen/classns3_1_1ndn_1_1ConsumerZipfMandelbrot.html """

import random
import numpy as np


class ZipfMandelbrotDistribution(object):
    """implements functions to get random numbers according to a ZipfMandelbrot distribution"""

    @staticmethod
    def create_zipf_mandelbrot_distribution(basis: int, improve_rank: float, power: float):
        """
        Creates a distribution array incl. values following a zipfmandelbrot like distribution
        :param basis the number of function names to create
        :param improve_rank the parameter of the improve rank (also expressed as q)
        :param power the parameter of the power (also expressed as s)
        """

        dist_array = np.zeros(basis + 1)  # create initial set of a distribution array

        # calculate some values according to the ZipfMandelbort distribution and store it in the array
        for i in range(1, basis + 1):
            dist_array[i] = dist_array[i - 1] + 1.0 / np.power(i + improve_rank, power)

        # afterwards, calculate the cumulative probability and print it to the console
        for i in range(1, basis + 1):
            dist_array[i] = dist_array[i] / dist_array[basis]
            #print("Cumulative probability [" + str(i) + "]=" + str(dist_array[i]))

        return dist_array

    @staticmethod
    def get_next_zipfmandelbrot_random_number(dist_array: np.ndarray, basis: int, seed: int = None):
        """
        Returns a value from the given distribution array.
        :param dist_array - the initialized array (see create_zipf_mandelbrot_distribution) containing the values
        :param basis - the number of function names to create to determine the next value to pass
        :param seed the seed if provided it is used by the random number generator to reproduce the distribution result
        :return
        """
        next_index = 1
        p_sum = 0

        rand = random.random()
        if seed is not None:
            rand = random.random(seed)

        while rand == 0:
            rand = random.random()

        for i in range(1, basis + 1):
            p_sum = dist_array[i]
            if rand <= p_sum:
                next_index = i
                break

        return next_index
