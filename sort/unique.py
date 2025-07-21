import json
import glob
import os

FIELDS_TO_REMOVE = [
    ("metadata", "rest_id"),
    ("metadata", "is_blue_verified"),
    ("metadata", "legacy", "followed_by"),
    ("metadata", "legacy", "following"),
    ("metadata", "legacy", "favourites_count"),
    ("metadata", "legacy", "followers_count"),
    ("metadata", "legacy", "listed_count"),
    ("metadata", "legacy", "name"),
    ("metadata", "legacy", "profile_banner_url"),
    ("metadata", "legacy", "profile_image_url_https"),
    ("metadata", "legacy", "screen_name"),
    ("metadata", "legacy", "statuses_count"),
    ("metadata", "legacy", "created_at"),
    ("metadata", "legacy", "normal_followers_count"),
    ("metadata", "legacy", "description")
]

def delete_nested_key(d, key_path):
    current = d
    for key in key_path[:-1]:
        if isinstance(current, dict) and key in current:
            current = current[key]
        else:
            return
    if isinstance(current, dict):
        current.pop(key_path[-1], None)

def move_location_field(item):
    try:
        location_value = item["metadata"]["legacy"].pop("location", None)
    except (KeyError, TypeError):
        location_value = None
    if location_value is None:
        return
    new_item = {}
    inserted = False
    for key, value in item.items():
        new_item[key] = value
        if key == "description" and not inserted:
            new_item["location"] = location_value
            inserted = True
    if not inserted:
        new_item["location"] = location_value
    item.clear()
    item.update(new_item)

def process_files(file_pattern, output_file):
    combined_data = []
    for filepath in glob.glob(file_pattern):
        with open(filepath, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
            if isinstance(data, list):
                for item in data:
                    move_location_field(item)
                    for key_path in FIELDS_TO_REMOVE:
                        delete_nested_key(item, key_path)
                combined_data.extend(data)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    process_files('./temp/twitter-Followers*.json', './temp/twitter-Followers.json')
    process_files('./temp/twitter-Following*.json', './temp/twitter-Following.json')
