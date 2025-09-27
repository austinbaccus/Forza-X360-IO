using System;
using System.IO;
using System.IO.Compression;
using System.Runtime.InteropServices;
using System.Text;

namespace ForzaStudioWinUI.Forza
{
    public class ZipFile
    {
        protected class Info
        {
            private Stream stream;

            internal int CompressedSize;

            private CompressionType compression;

            internal uint Crc;

            private string extraField;

            private short extraFieldLength;

            private short fileDate;

            private string fileName;

            private short fileNameLength;

            private short fileTime;

            private short flags;

            private int signature;

            internal int UncompressedSize;

            private short version;

            private byte[] data;

            [DllImport("xcompress.dll")]
            public static extern int XMemCreateDecompressionContext(XMemCodecType codecType, int pCodecParams, int flags, ref int pContext);

            [DllImport("xcompress.dll")]
            public static extern void XMemDestroyDecompressionContext(int context);

            [DllImport("xcompress.dll")]
            public static extern int XMemResetDecompressionContext(int context);

            [DllImport("xcompress.dll")]
            public static extern int XMemDecompressStream(int context, byte[] pDestination, ref int pDestSize, byte[] pSource, ref int pSrcSize);

            [DllImport("xcompress.dll")]
            public static extern int XMemCreateCompressionContext(XMemCodecType codecType, int pCodecParams, int flags, ref int pContext);

            [DllImport("xcompress.dll")]
            public static extern void XMemDestroyCompressionContext(int context);

            [DllImport("xcompress.dll")]
            public static extern int XMemResetCompressionContext(int context);

            [DllImport("xcompress.dll")]
            public static extern int XMemCompressStream(int context, byte[] pDestination, ref int pDestSize, byte[] pSource, ref int pSrcSize);

            public Info(Stream stream)
            {
                this.stream = stream;
                BinaryReader binaryReader = new BinaryReader(stream);
                signature = binaryReader.ReadInt32();
                version = binaryReader.ReadInt16();
                flags = binaryReader.ReadInt16();
                compression = (CompressionType)binaryReader.ReadInt16();
                fileTime = binaryReader.ReadInt16();
                fileDate = binaryReader.ReadInt16();
                Crc = binaryReader.ReadUInt32();
                CompressedSize = binaryReader.ReadInt32();
                UncompressedSize = binaryReader.ReadInt32();
                fileNameLength = binaryReader.ReadInt16();
                extraFieldLength = binaryReader.ReadInt16();
                fileName = Encoding.ASCII.GetString(binaryReader.ReadBytes(fileNameLength));
                extraField = Encoding.ASCII.GetString(binaryReader.ReadBytes(extraFieldLength));
                data = binaryReader.ReadBytes(CompressedSize);
            }

            public byte[] DecompressData()
            {
                byte[] array;
                switch (compression)
                {
                    case CompressionType.Stored:
                        return data;
                    case CompressionType.Deflate:
                        {
                            MemoryStream memoryStream = new MemoryStream(data);
                            DeflateStream deflateStream = new DeflateStream(memoryStream, CompressionMode.Decompress);
                            array = new byte[UncompressedSize];
                            if (deflateStream.Read(array, 0, UncompressedSize) != UncompressedSize)
                            {
                                throw new InvalidDataException("Decompression failed.");
                            }
                            break;
                        }
                    case CompressionType.LZX:
                        {
                            int pContext = 0;
                            XMemCreateDecompressionContext(XMemCodecType.LZX, 0, 0, ref pContext);
                            XMemResetDecompressionContext(pContext);
                            array = new byte[UncompressedSize];
                            XMemDecompressStream(pContext, array, ref UncompressedSize, data, ref CompressedSize);
                            XMemDestroyDecompressionContext(pContext);
                            break;
                        }
                    default:
                        throw new NotSupportedException($"Compression type of {compression} is currently not supported.");
                }
                if (ComputeCRC32(array) != Crc)
                {
                    throw new InvalidDataException("Invalid CRC detected.");
                }
                return array;
            }

            private static uint ComputeCRC32(byte[] bytes)
            {
                uint[] array = new uint[256];
                for (uint num = 0u; num < array.Length; num++)
                {
                    uint num2 = num;
                    for (int num3 = 8; num3 > 0; num3--)
                    {
                        num2 = (((num2 & 1) != 1) ? (num2 >> 1) : ((num2 >> 1) ^ 0xEDB88320u));
                    }
                    array[num] = num2;
                }
                uint num4 = uint.MaxValue;
                for (int i = 0; i < bytes.Length; i++)
                {
                    byte b = (byte)((num4 & 0xFF) ^ bytes[i]);
                    num4 = (num4 >> 8) ^ array[b];
                }
                return ~num4;
            }
        }

        private Stream stream;

        private int compressedSize;

        private CompressionType compression;

        private uint crc;

        private short diskNumberStart;

        private int externalAttributes;

        private string extraField;

        private short extraFieldLength;

        private short fileCommentLength;

        private short fileDate;

        private string fileName;

        private short fileNameLength;

        private short fileTime;

        private short flags;

        private int headerOffset;

        private short internalAttributes;

        private int signature;

        private int uncompressedSize;

        private short versionMadeBy;

        private short versionToExtract;

        private int offset;

        public string FileName
        {
            get
            {
                return fileName;
            }
            set
            {
                fileName = value;
                fileNameLength = (short)fileName.Length;
            }
        }

        public byte[] Data
        {
            get
            {
                stream.Seek(headerOffset, SeekOrigin.Begin);
                Info info = new Info(stream);
                return info.DecompressData();
            }
        }

        public ZipFile(Stream stream)
        {
            this.stream = stream;
            BinaryReader binaryReader = new BinaryReader(stream);
            offset = (int)stream.Position;
            signature = binaryReader.ReadInt32();
            versionMadeBy = binaryReader.ReadInt16();
            versionToExtract = binaryReader.ReadInt16();
            flags = binaryReader.ReadInt16();
            compression = (CompressionType)binaryReader.ReadInt16();
            fileTime = binaryReader.ReadInt16();
            fileDate = binaryReader.ReadInt16();
            crc = binaryReader.ReadUInt32();
            compressedSize = binaryReader.ReadInt32();
            uncompressedSize = binaryReader.ReadInt32();
            fileNameLength = binaryReader.ReadInt16();
            extraFieldLength = binaryReader.ReadInt16();
            fileCommentLength = binaryReader.ReadInt16();
            diskNumberStart = binaryReader.ReadInt16();
            internalAttributes = binaryReader.ReadInt16();
            externalAttributes = binaryReader.ReadInt32();
            headerOffset = binaryReader.ReadInt32();
            fileName = Encoding.ASCII.GetString(binaryReader.ReadBytes(fileNameLength));
            extraField = Encoding.ASCII.GetString(binaryReader.ReadBytes(extraFieldLength));
        }

        public void SaveAs(string filename)
        {
            using FileStream fileStream = new FileStream(filename, FileMode.Create, FileAccess.Write, FileShare.None);
            byte[] data = Data;
            fileStream.Write(data, 0, data.Length);
        }
    }
}
