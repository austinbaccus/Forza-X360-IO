using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace ForzaStudioWinUI.Forza
{
    public class ForzaArchive : IDisposable
    {
        protected class EndLocator
        {
            private Stream stream;

            private string comment;

            private short commentLength;

            internal int DirectoryOffset;

            private int directorySize;

            private short diskNumber;

            internal short EntriesInDirectory;

            private short entriesOnDisk;

            private int signature;

            private short startDiskNumber;

            public EndLocator(Stream stream)
            {
                this.stream = stream;
                BinaryReader binaryReader = new BinaryReader(stream);
                signature = binaryReader.ReadInt32();
                diskNumber = binaryReader.ReadInt16();
                startDiskNumber = binaryReader.ReadInt16();
                entriesOnDisk = binaryReader.ReadInt16();
                EntriesInDirectory = binaryReader.ReadInt16();
                directorySize = binaryReader.ReadInt32();
                DirectoryOffset = binaryReader.ReadInt32();
                commentLength = binaryReader.ReadInt16();
                comment = Encoding.ASCII.GetString(binaryReader.ReadBytes(commentLength));
            }

            public void Write(Stream ew)
            {
                BinaryWriter binaryWriter = new BinaryWriter(stream);
                binaryWriter.Write(signature);
                binaryWriter.Write(diskNumber);
                binaryWriter.Write(startDiskNumber);
                binaryWriter.Write(entriesOnDisk);
                binaryWriter.Write(EntriesInDirectory);
                binaryWriter.Write(directorySize);
                binaryWriter.Write(DirectoryOffset);
                binaryWriter.Write(commentLength);
                binaryWriter.Write(comment);
            }
        }

        private Stream io;

        private List<ZipFile> files = new List<ZipFile>();

        public ZipFile this[string path]
        {
            get
            {
                foreach (ZipFile file in files)
                {
                    if (file.FileName.Equals(path, StringComparison.InvariantCultureIgnoreCase))
                    {
                        return file;
                    }
                }
                return null;
            }
        }

        public List<ZipFile> Files
        {
            get
            {
                return files;
            }
            set
            {
                files = value;
            }
        }

        private Stream Io
        {
            get
            {
                return io;
            }
            set
            {
                io = value;
            }
        }

        public ForzaArchive(string file)
        {
            Initialize(new FileStream(file, FileMode.Open, FileAccess.Read, FileShare.Read));
        }

        public ForzaArchive(Stream stream)
        {
            Initialize(stream);
        }

        ~ForzaArchive()
        {
            Dispose();
        }

        private void Initialize(Stream stream)
        {
            io = stream;
            BinaryReader binaryReader = new BinaryReader(io);
            io.Seek((int)io.Length - 22, SeekOrigin.Begin);
            if (binaryReader.ReadInt32() != 101010256)
            {
                throw new InvalidDataException("This is not a valid Xbox 360 archive.");
            }
            io.Seek((int)io.Length - 22, SeekOrigin.Begin);
            EndLocator endLocator = new EndLocator(io);
            io.Seek(endLocator.DirectoryOffset, SeekOrigin.Begin);
            for (int i = 0; i < endLocator.EntriesInDirectory; i++)
            {
                files.Add(new ZipFile(io));
            }
        }

        public void Dispose()
        {
            if (io != null)
            {
                io.Dispose();
            }
            files = null;
        }

        public static byte[] GetFileData(string archivePath, string filePath)
        {
            try
            {
                using ForzaArchive forzaArchive = new ForzaArchive(archivePath);
                return forzaArchive[filePath].Data;
            }
            catch (Exception)
            {
                return null;
            }
        }
    }
}
