using SharpDX.Direct3D9;
using System;

namespace Forza
{
    public struct ForzaVertex
    {
        public Vector3? position;

        public Vector2? texture0;

        public Vector2? texture1;

        public Vector3? normal;

        public static VertexElement[] VertexElements = new VertexElement[5]
        {
            new VertexElement(0, 0, DeclarationType.Float3, DeclarationMethod.Default, DeclarationUsage.Position, 0),
            new VertexElement(0, 12, DeclarationType.Float2, DeclarationMethod.Default, DeclarationUsage.TextureCoordinate, 0),
            new VertexElement(0, 20, DeclarationType.Float2, DeclarationMethod.Default, DeclarationUsage.TextureCoordinate, 1),
            new VertexElement(0, 28, DeclarationType.Float3, DeclarationMethod.Default, DeclarationUsage.Normal, 0),
            new VertexElement(0, 40, DeclarationType.Color, DeclarationMethod.Default, DeclarationUsage.Color, 0)
        };

        public static int SizeInBytes = 44;

        public ForzaVertex(ForzaVersion version, ForzaVertexType type, EndianStream stream, uint size)
        {
            position = default;
            texture0 = default;
            texture1 = default;
            normal = default;
            switch (type)
            {
                case ForzaVertexType.Car:
                    switch (version)
                    {
                        case ForzaVersion.FM2:
                            if (size == 60)
                            {
                                float x = ConvertHalfToFloat(stream.ReadUInt16());
                                float y = ConvertHalfToFloat(stream.ReadUInt16());
                                float z = ConvertHalfToFloat(stream.ReadUInt16());
                                float num = ConvertHalfToFloat(stream.ReadUInt16());
                                position = new Vector3(x * num, y * num, z * num);
                                texture0 = new Vector2(ConvertHalfToFloat(stream.ReadUInt16()), ConvertHalfToFloat(stream.ReadUInt16()));
                                texture1 = new Vector2(ConvertHalfToFloat(stream.ReadUInt16()), ConvertHalfToFloat(stream.ReadUInt16()));
                                normal = ToN3(stream.ReadUInt32());
                                stream.Position += 4L;
                                stream.Position += 4L;
                                stream.Position += 32L;
                                break;
                            }
                            throw new NotSupportedException();
                        case ForzaVersion.FM3:
                            switch (size)
                            {
                                case 16u:
                                    {
                                        float x = ConvertHalfToFloat(stream.ReadUInt16());
                                        float y = ConvertHalfToFloat(stream.ReadUInt16());
                                        float z = ConvertHalfToFloat(stream.ReadUInt16());
                                        float num = ConvertHalfToFloat(stream.ReadUInt16());
                                        position = new Vector3(x * num, y * num, z * num);
                                        texture0 = new Vector2(ConvertHalfToFloat(stream.ReadUInt16()), ConvertHalfToFloat(stream.ReadUInt16()));
                                        normal = ToN3(stream.ReadUInt32());
                                        break;
                                    }
                                case 40u:
                                    {
                                        float x = ConvertHalfToFloat(stream.ReadUInt16());
                                        float y = ConvertHalfToFloat(stream.ReadUInt16());
                                        float z = ConvertHalfToFloat(stream.ReadUInt16());
                                        float num = ConvertHalfToFloat(stream.ReadUInt16());
                                        position = new Vector3(x * num, y * num, z * num);
                                        texture0 = new Vector2(ConvertHalfToFloat(stream.ReadUInt16()), ConvertHalfToFloat(stream.ReadUInt16()));
                                        texture1 = new Vector2(ConvertHalfToFloat(stream.ReadUInt16()), ConvertHalfToFloat(stream.ReadUInt16()));
                                        normal = ToN3(stream.ReadUInt32());
                                        stream.Position += 16L;
                                        ToN3(stream.ReadUInt32());
                                        break;
                                    }
                                case 44u:
                                    {
                                        float x = ConvertHalfToFloat(stream.ReadUInt16());
                                        float y = ConvertHalfToFloat(stream.ReadUInt16());
                                        float z = ConvertHalfToFloat(stream.ReadUInt16());
                                        float num = ConvertHalfToFloat(stream.ReadUInt16());
                                        position = new Vector3(x * num, y * num, z * num);
                                        texture0 = new Vector2(ConvertHalfToFloat(stream.ReadUInt16()), ConvertHalfToFloat(stream.ReadUInt16()));
                                        normal = ToN3(stream.ReadUInt32());
                                        stream.Position += 16L;
                                        ToN3(stream.ReadUInt32());
                                        stream.Position += 8L;
                                        break;
                                    }
                                default:
                                    throw new NotSupportedException();
                            }
                            break;
                        case ForzaVersion.FM4:
                            if (size == 32)
                            {
                                throw new NotSupportedException();
                                /*float x = ShortN(stream.ReadInt16());
                                float y = ShortN(stream.ReadInt16());
                                float z = ShortN(stream.ReadInt16());
                                float num = ShortN(stream.ReadInt16());
                                position = new Vector3(x * num, y * num, z * num);
                                texture0 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                texture1 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                Matrix matrix2 = Matrix.CreateFromQuaternion(new Quaternion(ShortN(stream.ReadInt16()), ShortN(stream.ReadInt16()), ShortN(stream.ReadInt16()), ShortN(stream.ReadInt16())));
                                normal = new Vector3(matrix2.M11, matrix2.M12, matrix2.M13);
                                new Vector3(matrix2.M21, matrix2.M22, matrix2.M23);
                                stream.Position += 4L;
                                stream.Position += 4L;*/
                                break;
                            }
                            throw new NotSupportedException();
                        case ForzaVersion.FH1:
                            if (size == 28)
                            {
                                throw new NotSupportedException();
                                /*float x = ShortN(stream.ReadInt16());
                                float y = ShortN(stream.ReadInt16());
                                float z = ShortN(stream.ReadInt16());
                                float num = ShortN(stream.ReadInt16());
                                position = new Vector3(x * num, y * num, z * num);
                                texture0 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                texture1 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                Matrix matrix = Matrix.CreateFromQuaternion(new Quaternion(ShortN(stream.ReadInt16()), ShortN(stream.ReadInt16()), ShortN(stream.ReadInt16()), ShortN(stream.ReadInt16())));
                                normal = new Vector3(matrix.M11, matrix.M12, matrix.M13);
                                new Vector3(matrix.M21, matrix.M22, matrix.M23);
                                stream.Position += 4L;*/
                                break;
                            }
                            throw new NotSupportedException();
                        default:
                            throw new NotSupportedException();
                    }
                    break;
                case ForzaVertexType.Track:
                    switch (size)
                    {
                        case 12u:
                            {
                                float x = stream.ReadSingle();
                                float y = stream.ReadSingle();
                                float z = stream.ReadSingle();
                                position = new Vector3(x, y, z);
                                break;
                            }
                        case 16u:
                            {
                                float x = stream.ReadSingle();
                                float y = stream.ReadSingle();
                                float z = stream.ReadSingle();
                                position = new Vector3(x, y, z);
                                normal = GetNormalized101010(stream.ReadUInt32());
                                break;
                            }
                        case 20u:
                            {
                                float x = stream.ReadSingle();
                                float y = stream.ReadSingle();
                                float z = stream.ReadSingle();
                                position = new Vector3(x, y, z);
                                normal = GetNormalized101010(stream.ReadUInt32());
                                texture0 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                break;
                            }
                        case 24u:
                            {
                                float x = stream.ReadSingle();
                                float y = stream.ReadSingle();
                                float z = stream.ReadSingle();
                                position = new Vector3(x, y, z);
                                normal = GetNormalized101010(stream.ReadUInt32());
                                texture0 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                texture1 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                break;
                            }
                        case 28u:
                            {
                                float x = stream.ReadSingle();
                                float y = stream.ReadSingle();
                                float z = stream.ReadSingle();
                                position = new Vector3(x, y, z);
                                normal = GetNormalized101010(stream.ReadUInt32());
                                texture0 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                stream.Position += 8L;
                                break;
                            }
                        case 32u:
                            {
                                float x = stream.ReadSingle();
                                float y = stream.ReadSingle();
                                float z = stream.ReadSingle();
                                position = new Vector3(x, y, z);
                                normal = GetNormalized101010(stream.ReadUInt32());
                                texture0 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                texture1 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                stream.Position += 8L;
                                break;
                            }
                        case 36u:
                            {
                                float x = stream.ReadSingle();
                                float y = stream.ReadSingle();
                                float z = stream.ReadSingle();
                                position = new Vector3(x, y, z);
                                normal = GetNormalized101010(stream.ReadUInt32());
                                stream.Position += 4L;
                                texture0 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                texture1 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                stream.Position += 8L;
                                break;
                            }
                        case 40u:
                            {
                                float x = stream.ReadSingle();
                                float y = stream.ReadSingle();
                                float z = stream.ReadSingle();
                                position = new Vector3(x, y, z);
                                normal = GetNormalized101010(stream.ReadUInt32());
                                texture0 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                texture1 = new Vector2(UShortN(stream.ReadUInt16()), UShortN(stream.ReadUInt16()));
                                stream.Position += 16L;
                                break;
                            }
                        default:
                            throw new NotSupportedException();
                    }
                    break;
                default:
                    throw new NotSupportedException();
            }
        }

        private float ShortN(short value)
        {
            return (float)value / 32767f;
        }

        private float UShortN(ushort value)
        {
            return (float)(int)value / 65535f;
        }

        /*private Vector3 GetNormalized101010(uint packedValue)
        {
            Normalized101010 normalized = new Normalized101010
            {
                PackedValue = packedValue
            };
            return normalized.ToVector3();
        }*/

        /*
        private static Vector3 GetNormalized101010(uint packedValue)
        {
            // Layout matches R10G10B10: bits [0..9]=X, [10..19]=Y, [20..29]=Z. Top 2 bits ignored.
            const int Mask10 = 0x3FF;   // 10-bit mask
            const int Sign10 = 0x200;   // bit 9 (sign bit in 10-bit two's complement)

            int ix = (int)(packedValue & Mask10);
            int iy = (int)((packedValue >> 10) & Mask10);
            int iz = (int)((packedValue >> 20) & Mask10);

            // Sign-extend from 10 bits to 32 bits
            ix = (ix & Sign10) != 0 ? ix | ~Mask10 : ix;
            iy = (iy & Sign10) != 0 ? iy | ~Mask10 : iy;
            iz = (iz & Sign10) != 0 ? iz | ~Mask10 : iz;

            // Convert SNORM10 -> float in [-1,1]; special-case the most negative
            static float Snorm10ToFloat(int v) => v == -512 ? -1.0f : v / 511.0f;

            return new Vector3(
                Snorm10ToFloat(ix),
                Snorm10ToFloat(iy),
                Snorm10ToFloat(iz)
            );
        }
        */

        private static Vector3 GetNormalized101010(uint packedValue)
        {
            const uint Mask10 = 0x3FFu;

            float x = (packedValue & Mask10) / 1023f;
            float y = ((packedValue >> 10) & Mask10) / 1023f;
            float z = ((packedValue >> 20) & Mask10) / 1023f;

            return new Vector3(x, y, z);
        }

        private unsafe float ConvertHalfToFloat(uint value)
        {
            uint num = 0u;
            uint num2 = 0u;
            num = value & 0x3FF;
            if ((value & 0x7C00) != 0)
            {
                num2 = (value >> 10) & 0x1F;
            }
            else if (num != 0)
            {
                num2 = 1u;
                do
                {
                    num2--;
                    num <<= 1;
                }
                while ((num & 0x400) == 0);
                num &= 0x3FF;
            }
            else
            {
                num2 = 4294967184u;
            }
            uint num3 = ((value & 0x8000) << 16) | (num2 + 112 << 23) | (num << 13);
            return *(float*)(&num3);
        }

        private Vector3 ToN3(uint u)
        {
            Vector3 zero = Vector3.Zero;
            uint[] array = new uint[2] { 0u, 4294965248u };
            uint[] array2 = new uint[2] { 0u, 4294966272u };
            uint num = u & 0x7FF;
            zero.X = (float)(short)(num | array[num >> 10]) / 1023f;
            num = (u >> 11) & 0x7FF;
            zero.Y = (float)(short)(num | array[num >> 10]) / 1023f;
            num = (u >> 22) & 0x3FF;
            zero.Z = (float)(short)(num | array2[num >> 9]) / 511f;
            return zero;
        }
    }
}
