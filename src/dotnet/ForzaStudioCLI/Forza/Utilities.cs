using System;
using System.Collections;

namespace Forza
{
    public static class Utilities
    {
        public static int CalculateFaceCount(int[] indices, IndexType type)
        {
            switch (type)
            {
                case IndexType.TriStrip:
                    {
                        int num = 0;
                        int num2 = 0;
                        while (num < indices.Length - 2)
                        {
                            if (indices[num + 2] != -1)
                            {
                                num++;
                                num2++;
                            }
                            else
                            {
                                num += 3;
                            }
                        }
                        return num2;
                    }
                case IndexType.TriList:
                    return indices.Length / 3;
                default:
                    throw new NotSupportedException("Unknown index type.");
            }
        }

        public static int CalculateVertexCount(int[] indices)
        {
            Hashtable hashtable = new Hashtable();
            foreach (int num in indices)
            {
                if (num != -1)
                {
                    hashtable[num] = 0;
                }
            }
            return hashtable.Count;
        }

        public static ForzaVertex[] GenerateVertices(ForzaVertex[] sectionVertices, ref int[] subSectionIndices)
        {
            int num = 0;
            Hashtable hashtable = new Hashtable();
            int num2 = subSectionIndices.Length;
            for (int i = 0; i < num2; i++)
            {
                int num3 = subSectionIndices[i];
                if (num3 != -1)
                {
                    if (hashtable[num3] == null)
                    {
                        hashtable[num3] = num;
                        num++;
                    }
                    subSectionIndices[i] = (int)hashtable[num3];
                }
            }
            ForzaVertex[] array = new ForzaVertex[num];
            foreach (DictionaryEntry item in hashtable)
            {
                ref ForzaVertex reference = ref array[(int)item.Value];
                reference = sectionVertices[(int)item.Key];
            }
            return array;
        }

        public static int[] GenerateTriangleList(int[] indices, int faceCount)
        {
            int[] array = new int[faceCount * 3];
            bool flag = true;
            int num = 0;
            int num2 = 0;
            while (num < indices.Length - 2)
            {
                int num3 = indices[num + 2];
                if (num3 != -1)
                {
                    int num4 = indices[num];
                    int num5 = indices[num + 1];
                    num++;
                    if (num4 != num5 && num5 != num3 && num4 != num3)
                    {
                        if (flag)
                        {
                            array[num2] = num4;
                            array[num2 + 1] = num5;
                            array[num2 + 2] = num3;
                        }
                        else
                        {
                            array[num2] = num5;
                            array[num2 + 1] = num4;
                            array[num2 + 2] = num3;
                        }
                    }
                    num2 += 3;
                    flag = !flag;
                }
                else
                {
                    flag = true;
                    num += 3;
                }
            }
            return array;
        }

        public static int[] ReadIndices(EndianStream stream, int count, int size)
        {
            int[] array = new int[count];
            for (int i = 0; i < array.Length; i++)
            {
                int num = ((size == 2) ? stream.ReadUInt16() : stream.ReadInt32());
                if ((size == 2 && num == 65535) || (size == 4 && num >= 16777215))
                {
                    num = -1;
                    array[i] = num;
                }
                else
                {
                    array[i] = num + ForzaCarSection.IBoffset;
                }
            }
            return array;
        }

        public static bool IsNullOrWhiteSpace(string s)
        {
            if (s != null)
            {
                return s.Trim().Length == 0;
            }
            return true;
        }

        public static void AssertEquals(byte obj1, byte obj2)
        {
            if (!obj1.Equals(obj2))
            {
                throw new Exception($"Analyze this! Expected: {obj2.ToString()}, Actual: {obj1.ToString()}");
            }
        }

        public static void AssertEquals(uint obj1, uint obj2)
        {
            if (!obj1.Equals(obj2))
            {
                throw new Exception($"Analyze this! Expected: {obj2.ToString()}, Actual: {obj1.ToString()}");
            }
        }

        public static void AssertEquals(float obj1, float obj2)
        {
            if (!obj1.Equals(obj2))
            {
                throw new Exception($"Analyze this! Expected: {obj2.ToString()}, Actual: {obj1.ToString()}");
            }
        }

        public static float CalculateBoundTargetValue(float actualValue, float actualMin, float actualMax, float targetMin, float targetMax)
        {
            if (actualValue > actualMax || actualValue < actualMin)
            {
                throw new ArgumentException("Actual value falls outside of actual range");
            }
            if (targetMin >= targetMax)
            {
                throw new ArgumentException("Invalid target range");
            }
            return targetMin + (actualValue - actualMin) / (actualMax - actualMin) * (targetMax - targetMin);
        }

        public static Vector3 CalculateBoundTargetValue(Vector3 actualValue, Vector3 actualMin, Vector3 actualMax, Vector3 targetMin, Vector3 targetMax)
        {
            return targetMin + (actualValue - actualMin) / (actualMax - actualMin) * (targetMax - targetMin);
        }
    }

}
