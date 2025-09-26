namespace ForzaStudio;

public class ComboBoxItem<T>
{
	public string Label { get; set; }

	public T Value { get; set; }

	public ComboBoxItem(T value, string label)
	{
		Value = value;
		Label = label;
	}

	public override string ToString()
	{
		return Label ?? string.Empty;
	}
}
