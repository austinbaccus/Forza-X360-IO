using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text;
using System.Threading.Tasks;

namespace ForzaStudioWinUI.Forza
{
    public class ForzaCarBin : ForzaResource
    {
        public EndianStream Stream;

        public ForzaCarSection[] Sections;

        public uint TypeId;

        public static bool f2ibend;

        public string tempName;

        public static int glassVertexCount;

        public static uint glassVertexSize;

        public static int bodyVertexCount;

        public static uint bodyVertexSize;

        public static ForzaVertex[] glassVertices;

        public static ForzaVertex[] bodyVertices;

        public static int glassIBoffset;

        public static int bodyIBoffset;

        public ForzaCarBin(string archivePath, string filePath)
            : base(filePath, archivePath)
        {
            Initialize();
        }

        public ForzaCarBin(string filePath)
            : base(filePath)
        {
            Initialize();
        }

        ~ForzaCarBin()
        {
            Dispose();
        }

        public void Initialize()
        {
            Stream = new EndianStream(GetDataStream(), EndianType.BigEndian);
            glassIBoffset = 0;
            bodyIBoffset = 0;
            switch (base.Version = GetVersion(Stream))
            {
                case ForzaVersion.FM2:
                    {
                        TypeId = Stream.ReadUInt32();
                        if (Stream.ReadUInt32() != 714)
                        {
                            if (TypeId == 2)
                            {
                                Stream.Position += 256L;
                            }
                            else if (TypeId == 1)
                            {
                                Stream.Position += 20L;
                            }
                        }
                        Stream.Position += 4L;
                        Stream.Seek(Stream.ReadUInt32() * 140, SeekOrigin.Current);
                        Stream.Position += 108L;
                        uint num5 = Stream.ReadUInt32() * 2;
                        for (int m = 0; m < num5; m++)
                        {
                            Stream.Seek(Stream.ReadUInt32() * 4, SeekOrigin.Current);
                        }
                        Stream.Position += 4L;
                        Sections = new ForzaCarSection[Stream.ReadUInt32()];
                        long position = Stream.Position;
                        for (int n = 0; n < Sections.Length; n++)
                        {
                            uint num6 = Stream.ReadUInt32();
                            if (num6 != 713 && num6 != 2 && num6 != 5)
                            {
                                Stream.Position -= 4L;
                            }
                            Stream.Position += 36L;
                            Stream.Position += 28L;
                            Stream.Seek(Stream.ReadUInt32() * 16, SeekOrigin.Current);
                            Stream.Position += 4L;
                            Stream.Seek(Stream.ReadUInt32() * 2, SeekOrigin.Current);
                            Stream.Position += 12L;
                            tempName = Stream.ReadASCII(Stream.ReadByte());
                            Stream.Position += 4L;
                            Stream.Position += 4L;
                            Stream.Position += 4L;
                            Stream.Position += 4L;
                            Stream.Position += 4L;
                            uint num7 = Stream.ReadUInt32();
                            for (int num8 = 0; num8 < num7; num8++)
                            {
                                Stream.Position += 8L;
                                tempName = Stream.ReadASCII(Stream.ReadInt32());
                                Stream.Position += 4L;
                                Stream.Position += 4L;
                                Stream.Position += 4L;
                                Stream.Seek(Stream.ReadUInt32() * Stream.ReadUInt32(), SeekOrigin.Current);
                            }
                        }
                        Stream.Position += 8L;
                        glassVertexCount = Stream.ReadInt32();
                        glassVertexSize = Stream.ReadUInt32();
                        Stream.Position += 4L;
                        if (glassVertexCount > 0)
                        {
                            glassVertices = new ForzaVertex[glassVertexCount];
                            for (int num9 = 0; num9 < glassVertexCount; num9++)
                            {
                                ref ForzaVertex reference = ref glassVertices[num9];
                                reference = new ForzaVertex(ForzaVersion.FM2, ForzaVertexType.Car, Stream, glassVertexSize);
                            }
                        }
                        Stream.Position += 12L;
                        bodyVertexCount = Stream.ReadInt32();
                        bodyVertexSize = Stream.ReadUInt32();
                        Stream.Position += 4L;
                        if (bodyVertexCount > 0)
                        {
                            bodyVertices = new ForzaVertex[bodyVertexCount];
                            for (int num10 = 0; num10 < bodyVertexCount; num10++)
                            {
                                ref ForzaVertex reference2 = ref bodyVertices[num10];
                                reference2 = new ForzaVertex(ForzaVersion.FM2, ForzaVertexType.Car, Stream, bodyVertexSize);
                            }
                        }
                        Stream.Position = position;
                        for (int num11 = 0; num11 < Sections.Length; num11++)
                        {
                            Sections[num11] = new ForzaCarSection(this);
                            if (ForzaCarSection.glassOffset > glassIBoffset)
                            {
                                glassIBoffset = ForzaCarSection.glassOffset;
                            }
                            if (ForzaCarSection.bodyOffset > bodyIBoffset)
                            {
                                bodyIBoffset = ForzaCarSection.bodyOffset;
                            }
                        }
                        break;
                    }
                case ForzaVersion.FM3:
                    {
                        TypeId = Stream.ReadUInt32();
                        if (Stream.ReadUInt32() != 13)
                        {
                            if (TypeId == 1)
                            {
                                Stream.Position += 256L;
                            }
                            else if (TypeId == 2)
                            {
                                Stream.Position += 20L;
                            }
                        }
                        Stream.Position += 8L;
                        Stream.Seek(Stream.ReadUInt32() * 140, SeekOrigin.Current);
                        Stream.Position += 428L;
                        uint num12 = Stream.ReadUInt32() * 2;
                        for (int num13 = 0; num13 < num12; num13++)
                        {
                            Stream.Seek(Stream.ReadUInt32() * 4, SeekOrigin.Current);
                        }
                        Stream.Position += 4L;
                        Sections = new ForzaCarSection[Stream.ReadUInt32()];
                        for (int num14 = 0; num14 < Sections.Length; num14++)
                        {
                            Sections[num14] = new ForzaCarSection(this);
                        }
                        break;
                    }
                case ForzaVersion.FM4:
                    {
                        TypeId = Stream.ReadUInt32();
                        if (TypeId == 1)
                        {
                            Stream.Position += 860L;
                            Stream.Seek(Stream.ReadUInt32() * 4, SeekOrigin.Current);
                            Stream.Position += 8L;
                        }
                        else if (TypeId == 2)
                        {
                            Stream.Position += 348L;
                            uint num15 = Stream.ReadUInt32();
                            Stream.Position += 4L;
                            Stream.Position += num15 * 140;
                            Stream.Position += 832L;
                            uint num16 = Stream.ReadUInt32() * 2;
                            for (int num17 = 0; num17 < num16; num17++)
                            {
                                Stream.Seek(Stream.ReadUInt32() * 4, SeekOrigin.Current);
                            }
                            Stream.Position += 4L;
                        }
                        else if (TypeId == 3)
                        {
                            Stream.Position += 920L;
                            uint num18 = Stream.ReadUInt32() * 2;
                            for (int num19 = 0; num19 < num18; num19++)
                            {
                                Stream.Seek(Stream.ReadUInt32() * 4, SeekOrigin.Current);
                            }
                            Stream.Position += 4L;
                        }
                        uint num20 = Stream.ReadUInt32();
                        List<ForzaCarSection> list2 = new List<ForzaCarSection>();
                        for (int num21 = 0; num21 < num20; num21++)
                        {
                            try
                            {
                                list2.Add(new ForzaCarSection(this));
                            }
                            catch (Exception)
                            {
                            }
                        }
                        Sections = new ForzaCarSection[list2.Count];
                        for (int num22 = 0; num22 < Sections.Length; num22++)
                        {
                            Sections[num22] = list2[num22];
                        }
                        if (Sections.Length == 0)
                        {
                            throw new Exception("analyze this!");
                        }
                        _ = base.Name;
                        break;
                    }
                case ForzaVersion.FH1:
                    {
                        TypeId = Stream.ReadUInt32();
                        if (TypeId == 1)
                        {
                            Stream.Position += 860L;
                            Stream.Seek(Stream.ReadUInt32() * 4, SeekOrigin.Current);
                            Stream.Position += 8L;
                        }
                        else if (TypeId == 5)
                        {
                            Stream.Position += 336L;
                            Stream.Seek(Stream.ReadUInt32() * 32, SeekOrigin.Current);
                            Stream.Position += 12L;
                            uint num = Stream.ReadUInt32();
                            Stream.Position += 4L;
                            Stream.Position += num * 140;
                            Stream.Position += 832L;
                            uint num2 = Stream.ReadUInt32() * 2;
                            for (int i = 0; i < num2; i++)
                            {
                                Stream.Seek(Stream.ReadUInt32() * 4, SeekOrigin.Current);
                            }
                            Stream.Position += 4L;
                        }
                        else if (TypeId == 3)
                        {
                            Stream.Position += 920L;
                            uint num3 = Stream.ReadUInt32() * 2;
                            for (int j = 0; j < num3; j++)
                            {
                                Stream.Seek(Stream.ReadUInt32() * 4, SeekOrigin.Current);
                            }
                            Stream.Position += 4L;
                        }
                        uint num4 = Stream.ReadUInt32();
                        List<ForzaCarSection> list = new List<ForzaCarSection>();
                        for (int k = 0; k < num4; k++)
                        {
                            try
                            {
                                list.Add(new ForzaCarSection(this));
                            }
                            catch (Exception)
                            {
                            }
                        }
                        Sections = new ForzaCarSection[list.Count];
                        for (int l = 0; l < Sections.Length; l++)
                        {
                            Sections[l] = list[l];
                        }
                        if (Sections.Length == 0)
                        {
                            throw new Exception("analyze this!");
                        }
                        _ = base.Name;
                        break;
                    }
                default:
                    throw new NotSupportedException();
            }
            Stream.Dispose();
        }

        private ForzaVersion GetVersion(Stream stream)
        {
            long position = stream.Position;
            ForzaVersion result = ForzaVersion.Unknown;
            if (Stream.Length > 512)
            {
                Stream.Position = 0L;
                uint num = Stream.ReadUInt32();
                uint num2 = Stream.ReadUInt32();
                stream.Seek(72L, SeekOrigin.Begin);
                uint num3 = Stream.ReadUInt32();
                stream.Seek(112L, SeekOrigin.Begin);
                uint num4 = Stream.ReadUInt32();
                stream.Seek(260L, SeekOrigin.Begin);
                uint num5 = Stream.ReadUInt32();
                stream.Seek(340L, SeekOrigin.Begin);
                uint num6 = Stream.ReadUInt32();
                if ((num == 1 && num2 == 714) || (num == 2 && num5 == 714))
                {
                    result = ForzaVersion.FM2;
                }
                else if ((num == 2 && (num2 == 0 || num2 == 1)) || (num == 1 && num4 == 0))
                {
                    result = ForzaVersion.FM3;
                }
                else if ((num == 1 && num2 == 16) || (num == 2 && num6 == 16) || (num == 3 && num3 == 16))
                {
                    result = ForzaVersion.FM4;
                }
                else if ((num == 1 && num2 == 17) || num == 5 || (num == 3 && num3 == 17))
                {
                    result = ForzaVersion.FH1;
                }
            }
            stream.Position = position;
            return result;
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
