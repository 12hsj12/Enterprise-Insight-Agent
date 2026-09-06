OFFICIAL_DOMAINS = {
    "openai.com",
    "anthropic.com",
    "google.com",
    "microsoft.com",
    "baidu.com",
    "alibabacloud.com",
    "tencent.com",
    "huawei.com",
    "mi.com",
    "oppo.com",
    "vivo.com",
}

AUTHORITATIVE_DOMAINS = {
    "reuters.com",
    "apnews.com",
    "bbc.com",
    "nature.com",
    "science.org",
}

AUTHORITY_SCORES = {
    "official": 1.0,
    "authoritative_media": 0.85,
    "web": 0.6,
    "unknown": 0.3,
}