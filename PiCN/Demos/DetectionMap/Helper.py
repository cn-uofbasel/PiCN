import base64

import cv2
import os


class Helper:

    @staticmethod
    def video_to_frames(path: str):
        video_capture = cv2.VideoCapture(path)
        fps = video_capture.get(cv2.CAP_PROP_FPS)
        success, frame = video_capture.read()
        height, width = frame.shape[:2]

        # margin used for cropping
        margin = int((height - (width / 2))/ 2)

        frames = []
        count = 0
        while success and count < 2000:
            # for best results we crop the images to the same aspect ratio (2:1) as the images the network was trained on.
            frame = frame[margin:-margin, :, :]
            frames.append(frame)
            success, frame = video_capture.read()
            count += 1

        return fps, frames

    @staticmethod
    def frames_to_video(path_in: str, path_out: str, fps: int):
        frames = []
        size = (0,0)
        files = [f for f in os.listdir(path_in) if os.path.isfile(os.path.join(path_in, f))]

        f = files[0].split("/")[-1]
        n = sum(i.isalpha() for i in f.split(".")[0])

        files.sort(key=lambda x: int(x[n:-4]))

        for i in range(len(files)):
            filename = path_in + files[i]
            img = cv2.imread(filename)
            height, width, layers = img.shape
            size = (width, height)
            frames.append(img)

        # Make sure the given folder exists, if not create it
        if not os.path.exists(os.path.dirname(path_out)):
            os.makedirs(os.path.dirname(path_out))

        out = cv2.VideoWriter(path_out, cv2.VideoWriter_fourcc(*'avc1'), fps, size)

        for i in range(len(frames)):
            out.write(frames[i])
        out.release()

    @staticmethod
    def pre_process(image, output_width: int, aspect_ratio: float, filetype: str):
        if isinstance(image, str):
            image = cv2.imread(image)
        cropped_image = Helper.crop(image, aspect_ratio=aspect_ratio)
        resized_image = Helper.resize(cropped_image, output_width=output_width)
        base64_image = Helper.to_base64(resized_image, filetype)
        return base64_image

    @staticmethod
    def resize(image, output_width: int=None, resize_factor: float=None):
        if isinstance(image, str):
            image = cv2.imread(image)
        if output_width:
            h, w = image.shape[:2]
            ratio = output_width / w
            output_height = int(h * ratio)
            image = cv2.resize(image, (output_width, output_height), interpolation=cv2.INTER_AREA)
            return image
        elif resize_factor:
            return cv2.resize(image, None, fx=resize_factor, fy=resize_factor, interpolation=cv2.INTER_AREA)
        return image

    @staticmethod
    def crop(image, margin_y: int=0, margin_x: int=0, aspect_ratio: float=None):
        if isinstance(image, str):
            image = cv2.imread(image)
        if aspect_ratio:
            h, w = image.shape[:2]
            output_height = w / aspect_ratio
            margin_y = int((h - output_height) / 2)

        if margin_y > 0 and margin_x > 0:
            return image[margin_y:-margin_y, margin_x:-margin_x]
        elif margin_y > 0:
            return image[margin_y:-margin_y, :]
        elif margin_x > 0:
            return image[:, margin_x:-margin_x]
        return image

    @staticmethod
    def to_base64(image, filetype: str):
        if isinstance(image, str):
            image = cv2.imread(image)
        retval, buffer = cv2.imencode(filetype, image)
        if retval:
            return base64.b64encode(buffer)
        return None
