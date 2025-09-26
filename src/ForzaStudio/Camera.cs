using System;
using System.Windows.Forms;
using Microsoft.Xna.Framework;

namespace ForzaStudio;

public class Camera
{
	private Panel Viewport;

	public readonly Matrix World = Matrix.Identity;

	private bool hasChanged = true;

	private Vector3 Position;

	private Vector3 Velocity;

	public Vector3 ForwardDirection;

	public Vector3 VerticalDirection;

	public Vector3 HorizontalDirection;

	public Vector3 LookAt;

	private Vector2 LookAngle;

	private Vector2 LookVelocity;

	private float FieldOfView;

	public float SpeedScale;

	public float LookSpeedScale;

	private float MoveAcceleration;

	private float LookAcceleration;

	private float ZoomVelocity;

	private float ViewDistance;

	public float MaxLookAngle { get; set; }

	public float MinLookAngle { get; set; }

	public float MaxMoveSpeed { get; set; }

	public float MinMoveSpeed { get; set; }

	public float MaxLookSpeed { get; set; }

	public float MinLookSpeed { get; set; }

	public float MaxMoveAccel { get; set; }

	public float MinMoveAccel { get; set; }

	public float MaxLookAccel { get; set; }

	public float MinLookAccel { get; set; }

	public float MinFieldOfView { get; set; }

	public float MaxFieldOfView { get; set; }

	public Matrix View { get; set; }

	public Matrix Projection { get; set; }

	public bool HasChanged => hasChanged;

	public Camera(Panel viewport)
	{
		Viewport = viewport;
		SpeedScale = 1f;
		LookSpeedScale = 1f;
		MoveAcceleration = 0.9f;
		LookAcceleration = 0.9f;
		ZoomVelocity = 0f;
		ViewDistance = 2500f;
		MaxLookAngle = 1.57f;
		MinLookAngle = -1.57f;
		MaxMoveSpeed = 5f;
		MinMoveSpeed = 0.01f;
		MaxLookSpeed = 5f;
		MinLookSpeed = 0.01f;
		MaxMoveAccel = 1f;
		MinMoveAccel = 0.01f;
		MaxLookAccel = 1f;
		MinLookAccel = 0.01f;
		FieldOfView = DegreesToRadians(90f);
		MinFieldOfView = DegreesToRadians(0.05f);
		MaxFieldOfView = DegreesToRadians(120f);
		MoveTo(new Vector3(2.1f, 1.25f, 1.1f));
		LookTo(new Vector2(-2.75f, -0.4f));
	}

	public void MoveTo(Vector3 position)
	{
		Position = position;
		hasChanged = true;
	}

	public void LookTo(Vector2 direction)
	{
		LookAngle = direction;
		hasChanged = true;
	}

	public void ApplyForce(Vector3 force)
	{
		Velocity += force * SpeedScale * 0.5f;
	}

	public void ApplyLookForce(Vector2 force)
	{
		LookVelocity = force * LookSpeedScale * 4f;
	}

	public void ApplyZoomForce(float force)
	{
		ZoomVelocity += force;
	}

	public void Update(float screenWidth, float screenHeight)
	{
		Velocity -= Velocity * MoveAcceleration;
		LookVelocity -= LookVelocity * LookAcceleration;
		ZoomVelocity -= ZoomVelocity * 0.2f;
		hasChanged = (double)Math.Abs(Velocity.Length()) > 0.0001 || (double)Math.Abs(LookVelocity.Length()) > 0.0001 || (double)Math.Abs(ZoomVelocity) > 0.0001;
		Position += Velocity;
		LookAngle += LookVelocity;
		FieldOfView *= 1f + ZoomVelocity;
		LookAngle.X = (float)(((double)LookAngle.X / (Math.PI * 2.0) - (double)(int)((double)LookAngle.X / (Math.PI * 2.0))) * Math.PI * 2.0);
		LookAngle.Y = Clamp(LookAngle.Y, MinLookAngle, MaxLookAngle);
		FieldOfView = Clamp(FieldOfView, MinFieldOfView, MaxFieldOfView);
		float num = (float)Math.Sin(LookAngle.X);
		float num2 = (float)Math.Sin(LookAngle.Y);
		float num3 = (float)Math.Cos(LookAngle.X);
		float num4 = (float)Math.Cos(LookAngle.Y);
		float x = (float)Math.Cos(LookAngle.X + 1.57f);
		float z = (float)Math.Sin(LookAngle.X + 1.57f);
		ForwardDirection = new Vector3(num3 * num4, num2, num * num4);
		VerticalDirection = new Vector3((0f - num3) * num2, num4, (0f - num) * num2);
		HorizontalDirection = new Vector3(x, 0f, z);
		LookAt = Position + ForwardDirection;
		View = Matrix.CreateLookAt(Position, LookAt, new Vector3(0f, 1f, 0f));
		Projection = Matrix.CreatePerspectiveFieldOfView(FieldOfView, (float)Viewport.Width / (float)Viewport.Height, 0.0001f, ViewDistance);
	}

	public void Zoom(float scale)
	{
		FieldOfView = Clamp(FieldOfView * scale, MinFieldOfView, MaxFieldOfView);
	}

	private float DegreesToRadians(float degrees)
	{
		return (float)((double)degrees * (Math.PI / 180.0));
	}

	private float RadiansToDegrees(float radians)
	{
		return (float)((double)radians * (180.0 / Math.PI));
	}

	private float Clamp(float value, float lowerBound, float upperBound)
	{
		if (value > upperBound)
		{
			return upperBound;
		}
		if (value < lowerBound)
		{
			return lowerBound;
		}
		return value;
	}
}
