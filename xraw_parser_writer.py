import struct
import numpy as np

class XRawVolumeParser():
    """Parses a .xraw file into a dictionary."""

    color_channel_data_types = ["I", "i", "f"]

    def __init__(self, filepath) -> None:
        self.filepath = filepath
        self.file = open(self.filepath, "rb")
        self.data = None

    def __del__(self):
        self.file.close()

    def raise_error_if_file_not_valid(self):
        if str(self.file.read(4).decode('utf-8')) != "XRAW":
            raise ValueError("Can't recognize file format.")

    def read_byte_to_int(self):
        return int(struct.unpack("b", self.file.read(1))[0])
    def read_int(self):
        return int(struct.unpack("i", self.file.read(4))[0])
    def read_unsigned_int(self):
        return int(struct.unpack("I", self.file.read(4))[0])

    def read_header(self):
        self.raise_error_if_file_not_valid()
        
        self.color_channel_data_type = self.color_channel_data_types[self.read_byte_to_int()]
        self.num_of_color_channels = self.read_byte_to_int()
        self.bytes_per_channel = self.read_byte_to_int() // 8
        self.bytes_per_index = self.read_byte_to_int() // 8

        self.width = self.read_unsigned_int()
        self.height = self.read_unsigned_int()
        self.depth = self.read_unsigned_int()

        self.num_of_pallette_colors = self.read_unsigned_int()


    def read_voxel_buffer(self):
        self.voxels = np.zeros((self.width, self.height, self.depth))

        for z in range(self.depth):
            for y in range(self.height):
                for x in range(self.width):
                    self.voxels[x][y][z] = int.from_bytes(
                        self.file.read(self.bytes_per_index), byteorder='little')

    def read_palette_buffer(self):
        self.palette = np.zeros((self.num_of_pallette_colors, self.num_of_color_channels))

        for i in range(self.num_of_pallette_colors):
            for c in range(self.num_of_color_channels):
                bytes_data = self.file.read(self.bytes_per_channel)+(b"\x00"*(4-self.bytes_per_channel))
                value = struct.unpack(self.color_channel_data_type, bytes_data)[0]
                self.palette[i][c] = value

    def read_remaining_bytes(self):
        self.remaining_bytes = b""

        byte = self.file.read(1)
        while byte != b"":
            self.remaining_bytes+=byte
            byte = self.file.read(1)

    def parse(self, use_lists=False):
        if self.data: return self.data

        self.read_header()
        self.read_voxel_buffer()
        self.read_palette_buffer()
        self.read_remaining_bytes()

        self.data = {}
        self.data["width"] = self.width
        self.data["height"] = self.height
        self.data["depth"] = self.depth
        self.data["num_of_pallette_colors"] = self.num_of_pallette_colors

        self.data["voxels"] = self.voxels
        self.data["palette"] = self.palette

        if use_lists:
            self.data["voxels"] = self.data["voxels"].tolist()
            self.data["palette"] = self.data["palette"].tolist()

        return self.data


class XRawVolumeWriter():
    """Writes voxels and palette data into a .xraw file.
    
    "voxels" is an array of voxels with shape (Width,Height,Depth)
    here, voxel is a zero or an index of color in a palette.
    "palette" is an array of colors with shape (N,4) where N - number of colors, it cant be greater than 256. 
        color channel value also ranges from 0 to 256.
    """

    def __init__(self, voxels=None, palette=None) -> None:
        voxels = np.array(voxels) if voxels!=None else self.default_voxels
        palette = np.array(palette) if palette!=None else self.default_palette

        if len(voxels.shape)!=3:
            raise ValueError("voxel grid must be 3 dimensional")

        self.voxels = voxels
        self.palette = palette

        self.format_string = "XRAW"

        self.color_channel_data_type = XRawVolumeParser.color_channel_data_types[0]
        self.bytes_per_channel = 1
        self.bytes_per_index = 1

        self.width = self.voxels.shape[0]
        self.height = self.voxels.shape[1]
        self.depth = self.voxels.shape[2]

        self.num_of_pallette_colors = self.palette.shape[0]
        self.num_of_color_channels = self.palette.shape[1]
        

        self.file = None

    def __del__(self):
        if self.file: self.file.close()

    @property
    def default_palette(self):
        palette = np.full((256, 4), 255)
        return palette
    @property
    def default_voxels(self):
        voxels = np.zeros((1,1,1))
        return voxels

    def write_bytes(self, bytes_iterable):
        if not self.file: return
        self.file.write(bytes(bytes_iterable))
    def write_unsigned_int(self, int_number):
        if not self.file: return
        self.write_bytes(int_number.to_bytes(4, 'little', signed=False))

    def get_color_channel_data_type_index(self):
        return XRawVolumeParser.color_channel_data_types.index(self.color_channel_data_type)

    def write_header(self):
        if not self.file: return

        self.write_bytes(self.format_string.encode("utf-8"))
        
        self.write_bytes([self.get_color_channel_data_type_index()])
        self.write_bytes([self.num_of_color_channels])
        self.write_bytes([self.bytes_per_channel*8])
        self.write_bytes([self.bytes_per_index*8])

        self.write_unsigned_int(self.width)
        self.write_unsigned_int(self.height)
        self.write_unsigned_int(self.depth)

        self.write_unsigned_int(self.num_of_pallette_colors)

    def write_voxels(self):
        for z in range(self.depth):
            for y in range(self.height):
                for x in range(self.width):
                    self.write_bytes([self.voxels[x][y][z]])

    def write_palette(self):
        for i in range(self.num_of_pallette_colors):
            for c in range(self.num_of_color_channels):
                self.write_bytes([self.palette[i][c]])

    def write_file(self, filepath):
        self.file = open(filepath, "wb")

        self.write_header()
        self.write_voxels()
        self.write_palette()

        self.file.close()