import numpy as np
import base64
import cv2


class DetectionMapObject:
    def __init__(self, base64_image, lat, lon, bearing, scaling_factor_z: float=1, scaling_factor_x: float=1):
        self.base64_image = base64_image
        self.scaling_factor_z = scaling_factor_z
        self.scaling_factor_x = scaling_factor_x
        self.lat = lat
        self.lon = lon
        self.bearing = bearing

    @classmethod
    def from_string(cls, map_det_obj_str):
        image_string, lat, lon, bearing, scaling_factor_z, scaling_factor_x = map_det_obj_str.split(":")
        return cls(image_string, float(lat), float(lon), float(bearing), float(scaling_factor_z), float(scaling_factor_x))

    def to_string(self):
        strings = [self.base64_image.decode("utf-8"), str(self.lat), str(self.lon), str(self.bearing),
                   str(self.scaling_factor_z), str(self.scaling_factor_x)]
        return ":".join(strings)

    def unpack(self):
        array = np.frombuffer(base64.b64decode(self.base64_image), np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return image, self.lat, self.lon, self.bearing, self.scaling_factor_z, self.scaling_factor_x
