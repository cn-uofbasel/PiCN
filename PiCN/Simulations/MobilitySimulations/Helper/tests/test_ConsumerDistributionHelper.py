"""A test class for the ZipfMandelbrot distribution helper """

import unittest

from PiCN.Simulations.MobilitySimulations.Helper.ConsumerDistributionHelper import ZipfMandelbrotDistribution

class TestConsumerZipfMandelbrotDistributionHelper(unittest.TestCase):
    """test class for testing the behavior and results of the ConsumerZipfDistributionHelper class"""

    def test_create_zipf_mandelbrot_distribution(self):
        """tests if the creation of a ZipfMandelbrot distribution works"""
        calc_distribution = ZipfMandelbrotDistribution.create_zipf_mandelbrot_distribution(10, 0.7, 0.7)
        self.assertEqual(len(calc_distribution), 11, "should have in total 11 elements in the distribution array")
        self.assertEqual(calc_distribution[10], 1.0, "last element in the distribution array is 1.0")

    def test_get_next_zipf_mandelbrot_distribution_value(self):
        """tests if returning a next value from the distribution works"""
        calc_distribution = ZipfMandelbrotDistribution.create_zipf_mandelbrot_distribution(5, 0.7, 0.7)
        value1 = ZipfMandelbrotDistribution.get_next_zipfmandelbrot_random_number(calc_distribution, 10)
        self.assertIsNot(value1, 0, "should not be 0")
        self.assertTrue(1 <= value1 <= 5, "should be in range to the provided basis")