using System;
using System.Drawing;
using System.Drawing.Imaging;
using System.IO;
using System.Runtime.InteropServices;

namespace ForzaStudio;

public class ForzaTexture : ForzaResource
{
	[DllImport("xds.dll")]
	private unsafe static extern void GetTextureSize(byte* inputData, int inputSize, out int outputWidth, out int outputHeight);

	[DllImport("xds.dll")]
	private unsafe static extern void Create(byte* inputData, int inputSize, void* outputData);

	[DllImport("xds.dll")]
	private unsafe static extern bool ConvertToBitmap(byte* inputData, int inputSize, int d3dFormat, int width, int height, void* outputData);

	public ForzaTexture(string archivePath, string filePath)
		: base(filePath, archivePath)
	{
	}

	public ForzaTexture(string filePath)
		: base(filePath)
	{
	}

	private unsafe Image LoadXds(Stream stream)
	{
		int num = (int)stream.Length;
		byte[] array = new byte[num + 8192];
		fixed (byte* value = array)
		{
			uint num2 = new UIntPtr(value).ToUInt32();
			byte* ptr = (byte*)new UIntPtr((num2 + 4095) & 0xFFFFF000u).ToPointer();
			int num3 = (int)(new UIntPtr(ptr).ToUInt32() - num2);
			using MemoryStream memoryStream = new MemoryStream(array);
			using BinaryWriter binaryWriter = new BinaryWriter(memoryStream);
			memoryStream.Position = num3;
			binaryWriter.Write(16777216);
			binaryWriter.Write(1144150100);
			binaryWriter.Write(805306368);
			binaryWriter.Write(872415232);
			binaryWriter.Write(335544320);
			binaryWriter.Write(new byte[28]);
			stream.Read(array, num3 + 48, 52);
			if (BitConverter.ToInt32(array, num3 + 48) != 50331648 || BitConverter.ToInt32(array, num3 + 52) != 16777216)
			{
				throw new Exception("Not a valid XDS file");
			}
			stream.Read(array, num3 + 4096, num - 52);
			GetTextureSize(ptr, num, out var outputWidth, out var outputHeight);
			Bitmap bitmap = null;
			try
			{
				bitmap = new Bitmap(outputWidth, outputHeight, PixelFormat.Format32bppArgb);
				BitmapData bitmapData = bitmap.LockBits(new Rectangle(0, 0, outputWidth, outputHeight), ImageLockMode.ReadWrite, bitmap.PixelFormat);
				Create(ptr, num, bitmapData.Scan0.ToPointer());
				bitmap.UnlockBits(bitmapData);
				return bitmap;
			}
			catch (Exception)
			{
				bitmap?.Dispose();
				throw new Exception("Unable to load texture.");
			}
		}
	}

	private unsafe Image LoadBix(byte[] data, int width, int height, int format)
	{
		if (data != null && data.Length > 0 && width > 0 && height > 0 && format > 0)
		{
			Bitmap bitmap = null;
			try
			{
				bitmap = new Bitmap(width, height, PixelFormat.Format32bppArgb);
				BitmapData bitmapData = bitmap.LockBits(new Rectangle(0, 0, width, height), ImageLockMode.ReadWrite, bitmap.PixelFormat);
				fixed (byte* inputData = data)
				{
					if (!ConvertToBitmap(inputData, data.Length, format, width, height, bitmapData.Scan0.ToPointer()))
					{
						throw new Exception();
					}
					bitmap.UnlockBits(bitmapData);
					return bitmap;
				}
			}
			catch (Exception)
			{
				bitmap?.Dispose();
				throw new Exception("Unable to load texture.");
			}
		}
		throw new ArgumentException();
	}

	public Image GetImage()
	{
		try
		{
			if (base.FilePath.EndsWith(".xds", StringComparison.InvariantCultureIgnoreCase))
			{
				using (MemoryStream stream = new MemoryStream(GetData()))
				{
					return LoadXds(stream);
				}
			}
			if (base.FilePath.EndsWith(".bix", StringComparison.InvariantCultureIgnoreCase))
			{
				Path.GetDirectoryName(base.FilePath);
				string text = base.FilePath.Replace("_b.bix", string.Empty).Replace(".bix", string.Empty);
				string text2 = text + ".bix";
				string text3 = text + "_b.bix";
				byte[] array = null;
				byte[] array2 = null;
				if (Utilities.IsNullOrWhiteSpace(base.ArchivePath))
				{
					using (FileStream fileStream = new FileStream(text2, FileMode.Open, FileAccess.Read, FileShare.Read))
					{
						array = new byte[fileStream.Length];
						fileStream.Read(array, 0, array.Length);
					}
					using FileStream fileStream2 = new FileStream(text3, FileMode.Open, FileAccess.Read, FileShare.Read);
					array2 = new byte[fileStream2.Length];
					fileStream2.Read(array2, 0, array2.Length);
				}
				else
				{
					array = ForzaArchive.GetFileData(base.ArchivePath, text2);
					array2 = ForzaArchive.GetFileData(base.ArchivePath, text3);
				}
				uint width;
				uint height;
				uint format;
				using (EndianStream endianStream = new EndianStream(array, EndianType.BigEndian))
				{
					uint num = endianStream.ReadUInt32();
					if (num != 1112102960 && num != 1112102961)
					{
						throw new NotSupportedException("Unrecognized bix file format.");
					}
					width = endianStream.ReadUInt32();
					height = endianStream.ReadUInt32();
					endianStream.ReadUInt32();
					format = endianStream.ReadUInt32();
					endianStream.ReadUInt32();
					endianStream.ReadUInt32();
				}
				return LoadBix(array2, (int)width, (int)height, (int)format);
			}
			throw new NotSupportedException("Unknown file extension");
		}
		catch (Exception)
		{
		}
		return null;
	}

	public override void Dispose()
	{
	}
}
