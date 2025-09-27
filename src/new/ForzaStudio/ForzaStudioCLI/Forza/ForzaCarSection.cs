using System;
using System.IO;

namespace Forza
{
    public class ForzaCarSection
    {
        public EndianStream Stream;

        public string Name;

        public ForzaCarBin Parent;

        public ForzaCarSubSection[] SubSections;

        public int lodVertexCount;

        public uint lodVertexSize;

        public ForzaVertex[] lodVertices;

        public int vertexCount;

        public uint vertexSize;

        public ForzaVertex[] lod0Vertices;

        public uint vbTest1;

        public uint vbTest2;

        public int sectionMax;

        public static int glassOffset;

        public static int bodyOffset;

        public static int IBoffset;

        public ForzaCarSection(ForzaCarBin car)
        {
            Parent = car;
            Stream = car.Stream;
            if (Stream.Position + 100 > Stream.Length)
            {
                throw new Exception();
            }
            uint num = Stream.ReadUInt32();
            if (num != 713 && num != 2 && num != 5)
            {
                Stream.Position -= 4L;
            }
            Vector3 vector = new Vector3(Stream.ReadSingle(), Stream.ReadSingle(), Stream.ReadSingle());
            Vector3 targetMin = new Vector3(Stream.ReadSingle(), Stream.ReadSingle(), Stream.ReadSingle());
            Vector3 targetMax = new Vector3(Stream.ReadSingle(), Stream.ReadSingle(), Stream.ReadSingle());
            Stream.Position += 28L;
            Stream.Seek(Stream.ReadUInt32() * 16, SeekOrigin.Current);
            Stream.Position += 4L;
            Stream.Seek(Stream.ReadUInt32() * 2, SeekOrigin.Current);
            if (car.Version == ForzaVersion.FM3)
            {
                Stream.Position += 8L;
            }
            else if (car.Version == ForzaVersion.FM2 || car.Version == ForzaVersion.FM4 || car.Version == ForzaVersion.FH1)
            {
                Stream.Position += 4L;
                vbTest1 = Stream.ReadUInt32();
                vbTest2 = Stream.ReadUInt32();
            }
            Name = Stream.ReadASCII(Stream.ReadByte());
            Stream.Position += 4L;
            if (car.Version == ForzaVersion.FM2)
            {
                Stream.Position += 4L;
            }
            lodVertexCount = Stream.ReadInt32();
            lodVertexSize = Stream.ReadUInt32();
            if (lodVertexSize == 28)
            {
                Stream.Position += 8L;
            }
            if (lodVertexCount > 0)
            {
                lodVertices = new ForzaVertex[lodVertexCount];
                for (int i = 0; i < lodVertexCount; i++)
                {
                    ref ForzaVertex reference = ref lodVertices[i];
                    reference = new ForzaVertex(car.Version, ForzaVertexType.Car, Stream, lodVertexSize);
                }
            }
            Stream.Position += 4L;
            if (car.Version == ForzaVersion.FH1 && lodVertexSize != 28)
            {
                Stream.Position += 4L;
            }
            IBoffset = 0;
            if (car.Version == ForzaVersion.FM2 && vbTest1 == vbTest2)
            {
                IBoffset = ForzaCarBin.glassIBoffset;
            }
            else if (car.Version == ForzaVersion.FM2 && vbTest1 == 0)
            {
                IBoffset = ForzaCarBin.bodyIBoffset;
            }
            uint num2 = Stream.ReadUInt32();
            SubSections = new ForzaCarSubSection[num2];
            sectionMax = 0;
            for (int j = 0; j < num2; j++)
            {
                SubSections[j] = new ForzaCarSubSection(this);
                if (ForzaCarSubSection.subSImax > sectionMax)
                {
                    sectionMax = ForzaCarSubSection.subSImax;
                }
            }
            glassOffset = 0;
            bodyOffset = 0;
            if (car.Version == ForzaVersion.FM2 && vbTest1 == vbTest2)
            {
                lodVertexCount = ForzaCarBin.glassVertexCount;
                lodVertexSize = ForzaCarBin.glassVertexSize;
                lodVertices = ForzaCarBin.glassVertices;
                glassOffset = sectionMax + 1;
            }
            else if (car.Version == ForzaVersion.FM2 && vbTest1 == 0)
            {
                lodVertexCount = ForzaCarBin.bodyVertexCount;
                lodVertexSize = ForzaCarBin.bodyVertexSize;
                lodVertices = ForzaCarBin.bodyVertices;
                bodyOffset = sectionMax + 1;
            }
            else
            {
                Stream.Position += 4L;
                vertexCount = Stream.ReadInt32();
                vertexSize = Stream.ReadUInt32();
                if (vertexSize == 28)
                {
                    Stream.Position += 8L;
                }
                if (vertexCount > 0)
                {
                    lod0Vertices = new ForzaVertex[vertexCount];
                    for (int k = 0; k < vertexCount; k++)
                    {
                        ref ForzaVertex reference2 = ref lod0Vertices[k];
                        reference2 = new ForzaVertex(car.Version, ForzaVertexType.Car, Stream, vertexSize);
                    }
                }
            }
            if (car.Version == ForzaVersion.FM4)
            {
                Stream.Position += 9L;
                Stream.Seek(Stream.ReadUInt32() * Stream.ReadUInt32(), SeekOrigin.Current);
                Stream.Position += 4L;
                Stream.Seek(Stream.ReadUInt32() * Stream.ReadUInt32(), SeekOrigin.Current);
            }
            else if (car.Version == ForzaVersion.FH1)
            {
                Stream.Position += 9L;
                if (lodVertexSize == 28)
                {
                    Stream.Position += 4L;
                }
                Stream.Seek(Stream.ReadUInt32() * Stream.ReadUInt32(), SeekOrigin.Current);
                Stream.Position += 8L;
                Stream.Seek(Stream.ReadUInt32() * Stream.ReadUInt32(), SeekOrigin.Current);
                Stream.Position += 8L;
            }
            BoundingBox boundingBox = BoundingBox.FromVertices(lod0Vertices);
            BoundingBox boundingBox2 = BoundingBox.FromVertices(lodVertices);
            ForzaCarSubSection[] subSections = SubSections;
            foreach (ForzaCarSubSection forzaCarSubSection in subSections)
            {
                forzaCarSubSection.Vertices = Utilities.GenerateVertices((forzaCarSubSection.Lod == 0) ? lod0Vertices : lodVertices, ref forzaCarSubSection.Indices);
                for (int m = 0; m < forzaCarSubSection.Vertices.Length; m++)
                {
                    if (targetMin.Length() > 0f && targetMax.Length() > 0f && car.Version != ForzaVersion.FM2)
                    {
                        if (forzaCarSubSection.Lod == 0)
                        {
                            forzaCarSubSection.Vertices[m].position = Utilities.CalculateBoundTargetValue(forzaCarSubSection.Vertices[m].position, boundingBox.Min, boundingBox.Max, targetMin, targetMax);
                        }
                        else
                        {
                            forzaCarSubSection.Vertices[m].position = Utilities.CalculateBoundTargetValue(forzaCarSubSection.Vertices[m].position, boundingBox2.Min, boundingBox2.Max, targetMin, targetMax);
                        }
                    }
                    forzaCarSubSection.Vertices[m].position += vector;
                    if (car.Version == ForzaVersion.FM2)
                    {
                        if (Math.Abs(forzaCarSubSection.Vertices[m].texture0.X) < 12800f)
                        {
                            forzaCarSubSection.Vertices[m].texture0.X = 0f - forzaCarSubSection.Vertices[m].texture0.X * 12800f;
                        }
                        else
                        {
                            forzaCarSubSection.Vertices[m].texture0.X = 0f - forzaCarSubSection.Vertices[m].texture0.X / 12800f;
                        }
                        if (Math.Abs(forzaCarSubSection.Vertices[m].texture0.Y) < 12800f)
                        {
                            forzaCarSubSection.Vertices[m].texture0.Y = 1f + forzaCarSubSection.Vertices[m].texture0.Y * 12800f;
                        }
                        else
                        {
                            forzaCarSubSection.Vertices[m].texture0.Y = 1f + forzaCarSubSection.Vertices[m].texture0.Y / 12800f;
                        }
                        if (Math.Abs(forzaCarSubSection.Vertices[m].texture1.X) < 12800f)
                        {
                            forzaCarSubSection.Vertices[m].texture1.X = 0f - forzaCarSubSection.Vertices[m].texture1.X * 12800f;
                        }
                        else
                        {
                            forzaCarSubSection.Vertices[m].texture1.X = 0f - forzaCarSubSection.Vertices[m].texture1.X / 12800f;
                        }
                        if (Math.Abs(forzaCarSubSection.Vertices[m].texture1.Y) < 12800f)
                        {
                            forzaCarSubSection.Vertices[m].texture1.Y = 1f + forzaCarSubSection.Vertices[m].texture1.Y * 12800f;
                        }
                        else
                        {
                            forzaCarSubSection.Vertices[m].texture1.Y = 1f + forzaCarSubSection.Vertices[m].texture1.Y / 12800f;
                        }
                    }
                    else
                    {
                        forzaCarSubSection.Vertices[m].texture0.X = forzaCarSubSection.Vertices[m].texture0.X * forzaCarSubSection.XUVScale + forzaCarSubSection.XUVOffset;
                        forzaCarSubSection.Vertices[m].texture0.Y = 1f - (forzaCarSubSection.Vertices[m].texture0.Y * forzaCarSubSection.YUVScale + forzaCarSubSection.YUVOffset);
                        forzaCarSubSection.Vertices[m].texture1.X = forzaCarSubSection.Vertices[m].texture1.X * forzaCarSubSection.XUV2Scale + forzaCarSubSection.XUV2Offset;
                        forzaCarSubSection.Vertices[m].texture1.Y = 1f - (forzaCarSubSection.Vertices[m].texture1.Y * forzaCarSubSection.YUV2Scale + forzaCarSubSection.YUV2Offset);
                    }
                }
                forzaCarSubSection.Indices = Utilities.GenerateTriangleList(forzaCarSubSection.Indices, forzaCarSubSection.FaceCount);
            }
        }
    }
}
