using System;
using System.Collections.Generic;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace Forza
{
    public class ForzaTrackBin : ForzaResource
    {
        public EndianStream Stream;

        public ForzaTrackSection[] Sections;

        public string Type;

        public ForzaTrackBin(string archivePath, string filePath)
            : base(filePath, archivePath)
        {
            Initialize();
        }

        public ForzaTrackBin(string filePath)
            : base(filePath)
        {
            Initialize();
        }

        ~ForzaTrackBin()
        {
            Dispose();
        }

        public void Initialize()
        {
            Stream = new EndianStream(GetDataStream(), EndianType.BigEndian);
            base.Name = base.FileName;
            switch (Stream.ReadUInt32())
            {
                case 4u:
                    base.Version = ForzaVersion.FM3;
                    break;
                case 6u:
                    base.Version = ForzaVersion.FM4;
                    break;
            }
            Stream.Position += 112L;
            uint num = Stream.ReadUInt32();
            Sections = new ForzaTrackSection[num];
            for (int i = 0; i < Sections.Length; i++)
            {
                Sections[i] = new ForzaTrackSection(this);
            }
            Stream.Dispose();
        }

        public override void Dispose()
        {
            if (Stream != null)
            {
                Stream.Dispose();
            }
            Sections = null;
        }
    }
}