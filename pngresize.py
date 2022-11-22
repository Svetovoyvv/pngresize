from binascii import crc32
from argparse import ArgumentParser

args = ArgumentParser()
args.add_argument('file', help='PNG file to resize path')
args.add_argument('--width', help='new width', type=int, default=0)
args.add_argument('--height', help='new height', type=int, default=0)
args.add_argument('-o', '--output', help='output file path', default=None)
args = args.parse_args()

output = args.output or args.file + '.resized.png'

class PNGChunk:
    def __init__(self, data: bytes | bytearray, offset: int = 0):
        data = data[offset:]
        self._size = int.from_bytes(data[:4], 'big')
        data = data[:self._size + 12]
        self._type = data[4:8].decode('ascii')
        self._data = data[8:-4]
        self._crc = int.from_bytes(data[-4:], 'big')
        self._source = data[:]
    @property
    def size(self) -> int:
        return self._size
    @property
    def type(self) -> str:
        return self._type
    @property
    def data(self) -> bytes:
        return self._data
    @data.setter
    def data(self, data: bytes):
        self._data = data
        self._size = len(data) + 12
    def to_bytes(self) -> bytes:
        return b"".join([
            self._size.to_bytes(4, 'big'),
            self._type.encode('ascii'),
            self._data,
            self.crc.to_bytes(4, 'big')
        ])
    @property
    def crc(self) -> int:
        return crc32(self._type.encode('ascii') + self._data)

class IHDRChunk(PNGChunk):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._width = int.from_bytes(self._data[:4], 'big')
        self._height = int.from_bytes(self._data[4:8], 'big')
        self._bit_depth = self._data[8]
        self._color_type = self._data[9]
        self._compression_method = self._data[10]
        self._filter_method = self._data[11]
        self._interlace_method = self._data[12]

    @property
    def width(self) -> int:
        return self._width
    @width.setter
    def width(self, width: int):
        self._width = width
        self._data = width.to_bytes(4, 'big') + self._data[4:]
    @property
    def height(self) -> int:
        return self._height
    @height.setter
    def height(self, height: int):
        self._height = height
        self._data = self._data[:4] + height.to_bytes(4, 'big') + self._data[8:]


def main():
    try:
        with open(args.file, 'rb') as f:
            data = f.read()
    except IOError as e:
        print('Error reading file:', e)
        exit(1)
    if not data.startswith(b'\x89PNG\x0d\x0a\x1a\x0a'):
        print('Invalid PNG file')
        exit(1)
    offset = 8
    while True:
        chunk = PNGChunk(data, offset)
        if chunk.type == 'IHDR':
            print('IHDR chunk found')
            break
        if offset >= len(data):
            print('IHDR chunk not found')
            exit(1)
        offset += chunk.size

    chunk = IHDRChunk(data, offset)
    print(offset)
    if args.width == 0:
        args.width = chunk.width
    if args.height == 0:
        args.height = chunk.height
    if args.width == chunk.width and args.height == chunk.height:
        print('Current size:')
        print(f'\tWidth: {chunk.width}')
        print(f'\tHeight: {chunk.height}')
        print('Nothing to do')
        exit(0)
    print('Updating size')
    if chunk.width != args.width:
        print('\tWidth changed from', chunk.width, 'to', args.width)
        chunk.width = args.width
    if chunk.height != args.height:
        print('\tHeight changed from', chunk.height, 'to', args.height)
        chunk.height = args.height
    data = data[:offset] + chunk.to_bytes() + data[offset + len(chunk.to_bytes()):]
    print('IHDR chunk updated')
    print('NUM', *[hex(i)[2:].zfill(2) for i in range(len(chunk.to_bytes()))])
    print('SRC', *[hex(i)[2:].zfill(2) for i in chunk.to_bytes()])
    print('OUT', *[hex(i)[2:].zfill(2) for i in chunk._source])

    try:
        with open(output, 'wb') as f:
            f.write(data)
    except IOError as e:
        print('Error writing file:', e)
        exit(1)
    print('Success creating file:', output)

if __name__ == '__main__':
    main()
