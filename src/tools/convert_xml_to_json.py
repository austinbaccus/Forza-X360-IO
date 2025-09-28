import xmltodict
import json
import sys

def xml_to_json(xml_file, json_file):
    with open(xml_file, "r", encoding="utf-8") as f:
        xml_data = f.read()

    # Parse XML to OrderedDict
    parsed_data = xmltodict.parse(xml_data)

    # Convert OrderedDict to JSON string
    json_data = json.dumps(parsed_data, indent=4)

    # Write JSON to file
    with open(json_file, "w", encoding="utf-8") as f:
        f.write(json_data)

    print(f"Converted {xml_file} → {json_file}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python xml_to_json.py input.xml output.json")
    else:
        xml_to_json(sys.argv[1], sys.argv[2])
