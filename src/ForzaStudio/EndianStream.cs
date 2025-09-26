using System;
using System.IO;
using System.Text;

namespace ForzaStudio;

public class EndianStream : Stream
{
	private Stream @base;

	private BinaryReader reader;

	private BinaryWriter writer;

	private EndianType endian;

	public override long Position
	{
		get
		{
			return @base.Position;
		}
		set
		{
			@base.Position = value;
		}
	}

	public override bool CanRead => @base.CanRead;

	public override bool CanSeek => @base.CanSeek;

	public override bool CanWrite => @base.CanWrite;

	public override bool CanTimeout => @base.CanTimeout;

	public override long Length => @base.Length;

	public EndianStream(Stream stream, EndianType endian)
	{
		@base = stream;
		if (stream.CanRead)
		{
			reader = new BinaryReader(stream);
		}
		if (stream.CanWrite)
		{
			writer = new BinaryWriter(stream);
		}
		this.endian = endian;
	}

	public EndianStream(byte[] data, EndianType endian)
	{
		@base = new MemoryStream(data);
		if (@base.CanRead)
		{
			reader = new BinaryReader(@base);
		}
		if (@base.CanWrite)
		{
			writer = new BinaryWriter(@base);
		}
		this.endian = endian;
	}

	~EndianStream()
	{
		Dispose();
	}

	public new void Dispose()
	{
		if (@base != null)
		{
			@base.Dispose();
		}
		if (reader != null)
		{
			reader.Close();
		}
		if (writer != null)
		{
			writer.Close();
		}
	}

	public override void Flush()
	{
		@base.Flush();
	}

	public override long Seek(long offset, SeekOrigin origin)
	{
		return @base.Seek(offset, origin);
	}

	public override void SetLength(long value)
	{
		@base.SetLength(value);
	}

	public override int Read(byte[] buffer, int offset, int count)
	{
		return @base.Read(buffer, offset, count);
	}

	public override void Write(byte[] buffer, int offset, int count)
	{
		@base.Write(buffer, offset, count);
	}

	public bool ReadBoolean()
	{
		return reader.ReadBoolean();
	}

	public new byte ReadByte()
	{
		try
		{
			return reader.ReadByte();
		}
		catch (Exception)
		{
			return 0;
		}
	}

	public char ReadChar()
	{
		return reader.ReadChar();
	}

	public short ReadInt16()
	{
		if (endian == EndianType.BigEndian)
		{
			byte[] array = reader.ReadBytes(2);
			Array.Reverse(array);
			return BitConverter.ToInt16(array, 0);
		}
		return reader.ReadInt16();
	}

	public ushort ReadUInt16()
	{
		if (endian == EndianType.BigEndian)
		{
			byte[] array = reader.ReadBytes(2);
			Array.Reverse(array);
			return BitConverter.ToUInt16(array, 0);
		}
		return reader.ReadUInt16();
	}

	public int ReadInt32()
	{
		if (endian == EndianType.BigEndian)
		{
			byte[] array = reader.ReadBytes(4);
			Array.Reverse(array);
			return BitConverter.ToInt32(array, 0);
		}
		return reader.ReadInt32();
	}

	public uint ReadUInt32()
	{
		if (endian == EndianType.BigEndian)
		{
			byte[] array = reader.ReadBytes(4);
			Array.Reverse(array);
			return BitConverter.ToUInt32(array, 0);
		}
		return reader.ReadUInt32();
	}

	public long ReadInt64()
	{
		if (endian == EndianType.BigEndian)
		{
			byte[] array = reader.ReadBytes(8);
			Array.Reverse(array);
			return BitConverter.ToInt64(array, 0);
		}
		return reader.ReadInt64();
	}

	public ulong ReadUInt64()
	{
		if (endian == EndianType.BigEndian)
		{
			byte[] array = reader.ReadBytes(8);
			Array.Reverse(array);
			return BitConverter.ToUInt64(array, 0);
		}
		return reader.ReadUInt64();
	}

	public float ReadSingle()
	{
		if (endian == EndianType.BigEndian)
		{
			byte[] array = reader.ReadBytes(4);
			Array.Reverse(array);
			return BitConverter.ToSingle(array, 0);
		}
		return reader.ReadSingle();
	}

	public double ReadDouble()
	{
		if (endian == EndianType.BigEndian)
		{
			byte[] array = reader.ReadBytes(8);
			Array.Reverse(array);
			return BitConverter.ToDouble(array, 0);
		}
		return reader.ReadDouble();
	}

	public string ReadASCII(int length)
	{
		return Encoding.ASCII.GetString(reader.ReadBytes(length));
	}

	public string ReadString()
	{
		return reader.ReadString();
	}

	public byte[] ReadBytes(int count)
	{
		return reader.ReadBytes(count);
	}

	public void Write(byte[] data)
	{
		writer.Write(data);
	}

	public void Write(object obj)
	{
		switch (Convert.GetTypeCode(obj))
		{
		case TypeCode.Boolean:
		case TypeCode.Char:
		case TypeCode.Byte:
			writer.Write((byte)obj);
			break;
		case TypeCode.Int16:
		case TypeCode.UInt16:
			if (endian == EndianType.BigEndian)
			{
				byte[] bytes4 = BitConverter.GetBytes((ushort)obj);
				Array.Reverse(bytes4);
				writer.Write(bytes4);
			}
			else
			{
				writer.Write((ushort)obj);
			}
			break;
		case TypeCode.Int32:
		case TypeCode.UInt32:
			if (endian == EndianType.BigEndian)
			{
				byte[] bytes = BitConverter.GetBytes((uint)obj);
				Array.Reverse(bytes);
				writer.Write(bytes);
			}
			else
			{
				writer.Write((uint)obj);
			}
			break;
		case TypeCode.Int64:
		case TypeCode.UInt64:
			if (endian == EndianType.BigEndian)
			{
				byte[] bytes3 = BitConverter.GetBytes((ulong)obj);
				Array.Reverse(bytes3);
				writer.Write(bytes3);
			}
			else
			{
				writer.Write((ulong)obj);
			}
			break;
		case TypeCode.Single:
			if (endian == EndianType.BigEndian)
			{
				byte[] bytes5 = BitConverter.GetBytes((float)obj);
				Array.Reverse(bytes5);
				writer.Write(bytes5);
			}
			else
			{
				writer.Write((float)obj);
			}
			break;
		case TypeCode.Double:
			if (endian == EndianType.BigEndian)
			{
				byte[] bytes2 = BitConverter.GetBytes((double)obj);
				Array.Reverse(bytes2);
				writer.Write(bytes2);
			}
			else
			{
				writer.Write((double)obj);
			}
			break;
		case TypeCode.String:
			writer.Write(Encoding.ASCII.GetBytes((string)obj + "\0"));
			break;
		case TypeCode.Object:
			if (obj is byte[] buffer)
			{
				writer.Write(buffer);
				break;
			}
			throw new NotSupportedException("Invalid datatype.");
		default:
			throw new NotSupportedException("Invalid datatype.");
		}
	}
}
