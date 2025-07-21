import json
import glob
import os

# 直接写成顶层字段列表
FIELDS_TO_REMOVE = [
    "fast_followers_count",
    "normal_followers_count",
    "id_str",
    "utc_offset",
    "time_zone",
    "geo_enabled",
    "lang",
    "contributors_enabled",
    "is_translator",
    "is_translation_enabled",
    "profile_background_color",
    "profile_background_image_url_https",
    "profile_image_url_https",
    "profile_link_color",
    "profile_sidebar_border_color",
    "profile_sidebar_fill_color",
    "profile_text_color",
    "live_following",
    "blocking",
    "blocked_by",
]

def move_location_field(item):
    # 直接从顶层 pop 出来
    loc = item.pop("location", None)
    if loc is None:
        return
    # 我们想让它出现在 description 之后，重建一下 dict 顺序
    new_item = {}
    for k, v in item.items():
        new_item[k] = v
        if k == "description":
            new_item["location"] = loc
    # 如果 description 不在（或刚好在最后），就追加到末尾
    if "location" not in new_item:
        new_item["location"] = loc
    item.clear()
    item.update(new_item)

def process_files(file_pattern, output_file):
    combined = []
    for path in glob.glob(file_pattern):
        with open(path, encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue
        if isinstance(data, list):
            for item in data:
                # 先移动 location
                move_location_field(item)
                # 再删顶层字段
                for fld in FIELDS_TO_REMOVE:
                    item.pop(fld, None)
            combined.extend(data)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    process_files('./temp/followers_list.json', './temp/twitter-Followers.json')
    process_files('./temp/following_list.json', './temp/twitter-Following.json')
