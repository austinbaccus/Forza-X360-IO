using System;
using System.Collections.Generic;
using System.IO;

namespace Forza
{
    public abstract class ForzaResource : IDisposable
    {
        public Guid Id = Guid.NewGuid();

        public Dictionary<string, object> Tags = new Dictionary<string, object>();

        public ForzaVersion Version { get; set; }

        public string FilePath { get; protected set; }

        public string ArchivePath { get; protected set; }

        public string FileName => Path.GetFileNameWithoutExtension(FilePath).ToLowerInvariant();

        public string Extension => Path.GetExtension(FilePath).ToLowerInvariant();

        public string Name { get; set; }

        public string Description { get; set; }

        protected ForzaResource(string filePath, string archivePath = null)
        {
            if (filePath != null)
            {
                FilePath = filePath.ToLowerInvariant();
                if (archivePath != null)
                {
                    ArchivePath = archivePath.ToLowerInvariant();
                }
                return;
            }
            throw new ArgumentNullException("A file path must be specified");
        }

        public byte[] GetData()
        {
            try
            {
                if (!Utilities.IsNullOrWhiteSpace(ArchivePath) && 
                    !Utilities.IsNullOrWhiteSpace(FilePath) && 
                    File.Exists(ArchivePath))
                {
                    using (ForzaArchive forzaArchive = new ForzaArchive(ArchivePath))
                    {
                        // Unable to load DLL 'xcompress.dll' or one of its dependencies: The specified module could not be found.
                        return forzaArchive[FilePath].Data;
                    }
                }
                if (!Utilities.IsNullOrWhiteSpace(FilePath) && File.Exists(FilePath))
                {
                    using (FileStream fileStream = new FileStream(FilePath, FileMode.Open, FileAccess.Read, FileShare.Read))
                    {
                        byte[] array = new byte[fileStream.Length];
                        fileStream.Read(array, 0, array.Length);
                        return array;
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine(ex.Message);
            }
            return null;
        }

        public Stream GetDataStream()
        {
            byte[] data = GetData();
            if (data != null)
            {
                return new MemoryStream(data);
            }
            return null;
        }

        public abstract void Dispose();
    }
}
