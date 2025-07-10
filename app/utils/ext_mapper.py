

mime_extension_map = {
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/html": ".html",
    "text/csv": ".csv",
    "text/css": ".css",
    "text/javascript": ".js",
    "application/json": ".json",
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/xml": ".xml",
    "application/javascript": ".js",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/svg+xml": ".svg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/x-icon": ".ico",
    "audio/mpeg": ".mp3",
    "audio/wav": ".wav",  # 这里加上 wav
    "video/mp4": ".mp4",
    "video/quicktime": ".mov",
    "video/webm": ".webm",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    # 还可以继续补充
}

# 反向映射：后缀 => MIME
extension_mime_map = {v: k for k, v in mime_extension_map.items()}

timestamp_format_map = {
    "null": None,
    "full": "%Y%m%d_%H%M%S",
    "date": "%Y%m%d",
    "time": "%H%M%S",
    "year": "%Y",
    "month": "%m",
    "day": "%d",
    "hour": "%H",
    "minute": "%M",
    "second": "%S",
}

binary_extensions = {
    ".xlsx", ".xls", ".xlsm",
    ".docx", ".doc", ".pptx", ".ppt",
    ".pdf", ".epub",
    ".zip", ".rar", ".7z",
    ".png", ".jpg", ".jpeg", ".bmp", ".gif",
    ".mp3", ".mp4", ".mov", ".avi",
    ".exe", ".dll", ".bin",
}

text_extensions = {
        ".csv", ".tsv", ".txt", ".log", ".md", ".rst", ".ini", ".cfg",
        ".json", ".xml", ".yaml", ".yml",
        ".html", ".htm", ".xhtml",
        ".tex", ".rtf", ".srt",
        ".py", ".js", ".css", ".java", ".cpp", ".c", ".sh", ".bat"
    }


