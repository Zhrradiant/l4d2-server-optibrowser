import re
import requests
from urllib.parse import urlparse
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from language_strings import load_language_from_config, get_string

load_language_from_config()

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def extract_item_id(url):
    """从Steam工坊URL中提取ID（支持合集和物品链接）"""
    # 统一匹配id参数
    id_pattern = re.compile(r'[?&]id=(\d+)')
    match = id_pattern.search(url)
    if match:
        return match.group(1)

    # 处理短链接形式和新格式
    parsed = urlparse(url)
    if any(path in parsed.path for path in ['filedetails', 'sharedfiles', 'workshop']):
        # 尝试从查询参数中提取
        query_params = {}
        for part in parsed.query.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                query_params[key] = value
        if 'id' in query_params:
            return query_params['id']

    # 如果是纯数字ID，直接返回
    if re.match(r'^\d+$', url):
        return url

    return None


def get_workshop_items(url):
    """获取工坊内容（支持合集和单个物品）"""
    item_id = extract_item_id(url)
    if not item_id:
        return None, get_string("invalid_workshop_url", "无效的工坊链接")

    # 先尝试作为合集处理
    collection_api_url = "https://api.steampowered.com/ISteamRemoteStorage/GetCollectionDetails/v1/"
    try:
        response = requests.post(
            collection_api_url,
            data={
                "collectioncount": 1,
                "publishedfileids[0]": item_id
            },
            verify=False,
            timeout=15
        )
        data = response.json()
        collection_details = data.get("response", {}).get("collectiondetails", [])

        # 如果返回结果中有collectiondetails且不为空，说明是合集
        if collection_details and collection_details[0]:
            children = collection_details[0].get("children", [])
            if children:
                return [str(item["publishedfileid"]) for item in children], None
    except Exception as e:
        # 合集API调用失败，继续尝试作为单个物品
        print(f"合集API调用失败，作为单个物品处理: {str(e)}")

    # 如果不是合集或合集API调用失败，作为单个物品处理
    return [item_id], None


def get_item_details(item_id):
    """获取单个工坊物品详情"""
    api_url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"

    try:
        response = requests.post(
            api_url,
            data={
                "itemcount": 1,
                "publishedfileids[0]": item_id
            },
            verify=False,
            timeout=15
        )
        data = response.json()
        details = data["response"]["publishedfiledetails"][0]

        # 检查API返回状态
        if details.get("result") and details["result"] != 1:
            return None, get_string("item_unavailable", "工坊物品不可用或已被移除")

        return {
            "preview": details.get("preview_url", ""),
            "title": details.get("title", "未知标题"),
            "created": details.get("time_created", 0),
            "updated": details.get("time_updated", 0),
            "url": details.get("file_url", ""),
            "item_id": item_id,
            "file_size": details.get("file_size", 0)
        }, None

    except Exception as e:
        return None, get_string("get_item_details_failed_network",
                                f"获取物品详情失败，请检查是否可以连接Steam网络: {str(e)}")


def get_multiple_item_details(item_ids):
    """批量获取多个工坊物品详情"""
    if not item_ids:
        return [], None

    api_url = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"

    try:
        # 构建批量查询参数
        data = {"itemcount": len(item_ids)}
        for index, item_id in enumerate(item_ids):
            data[f"publishedfileids[{index}]"] = item_id

        response = requests.post(
            api_url,
            data=data,
            verify=False,
            timeout=15
        )
        data = response.json()
        all_details = data["response"]["publishedfiledetails"]

        results = []
        errors = []

        for details in all_details:
            # 检查API返回状态
            if details.get("result") and details["result"] != 1:
                errors.append(f"物品 {details.get('publishedfileid', '未知')} 不可用")
                continue

            results.append({
                "preview": details.get("preview_url", ""),
                "title": details.get("title", "未知标题"),
                "created": details.get("time_created", 0),
                "updated": details.get("time_updated", 0),
                "url": details.get("file_url", ""),
                "item_id": str(details.get("publishedfileid", "")),
                "file_size": details.get("file_size", 0)
            })

        error_msg = ", ".join(errors) if errors else None
        return results, error_msg

    except Exception as e:
        return None, get_string("get_multiple_items_failed", f"批量获取物品详情失败: {str(e)}")