#!/usr/bin/env python3
import copy
import json
import os
import sys
import urllib.request
import subprocess
import uuid
import time
from pathlib import Path
import mimetypes
from urllib.parse import urlencode

BASE_URL = os.environ.get('METERSPHERE_BASE_URL', '').rstrip('/')
AK = os.environ.get('METERSPHERE_ACCESS_KEY') or os.environ.get('METERSPHERE_ACCESS_KEY', '')
SK = os.environ.get('METERSPHERE_SECRET_KEY') or os.environ.get('METERSPHERE_SECRET_KEY', '')

METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH = os.environ.get('METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH', '/functional/case/add')
FUNCTIONAL_CASE_CREATE_PATH = METERSPHERE_FUNCTIONAL_CASE_CREATE_PATH


def die(msg):
    print(msg, file=sys.stderr)
    sys.exit(1)


def signature():
    plain = f"{AK}|{uuid.uuid4()}|{int(time.time()*1000)}"
    p = subprocess.run([
        'openssl', 'enc', '-aes-128-cbc', '-K', SK.encode().hex(), '-iv', AK.encode().hex(), '-base64', '-A', '-nosalt'
    ], input=plain.encode(), capture_output=True, check=True)
    return p.stdout.decode().strip()


def headers():
    if not BASE_URL or not AK or not SK:
        die('缺少 METERSPHERE_BASE_URL / METERSPHERE_ACCESS_KEY / METERSPHERE_SECRET_KEY')
    return {'Content-Type': 'application/json', 'accessKey': AK, 'signature': signature()}


def request_json(method, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(BASE_URL + path, data=data, headers=headers(), method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))

def request_multipart(method, path, fields=None, files=None):
    """发送multipart/form-data请求"""
    import io
    import random
    import string
    
    if fields is None:
        fields = {}
    if files is None:
        files = {}
    
    # 生成边界字符串
    boundary = '----WebKitFormBoundary' + ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    
    # 构建multipart数据
    data_parts = []
    
    # 添加字段
    for key, value in fields.items():
        data_parts.append(f'--{boundary}')
        data_parts.append(f'Content-Disposition: form-data; name="{key}"')
        data_parts.append('')
        data_parts.append(str(value))
    
    # 添加文件（如果有）
    for key, file_info in files.items():
        filename = file_info.get('filename', 'file')
        content = file_info.get('content', b'')
        content_type = file_info.get('content_type', 'application/octet-stream')
        
        data_parts.append(f'--{boundary}')
        data_parts.append(f'Content-Disposition: form-data; name="{key}"; filename="{filename}"')
        data_parts.append(f'Content-Type: {content_type}')
        data_parts.append('')
        data_parts.append('')  # 空行后是二进制内容
        
    data_parts.append(f'--{boundary}--')
    data_parts.append('')
    
    # 构建请求体
    body = '\r\n'.join(data_parts).encode('utf-8')
    
    # 如果是文件，需要特殊处理
    if files:
        # 对于文件上传，我们需要构建真正的multipart数据
        import tempfile
        import io as io_module
        
        # 创建临时文件来构建multipart数据
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as tmp:
            # 写入boundary
            for part in data_parts[:-2]:  # 排除最后的boundary结束标记
                tmp.write(part.encode('utf-8') + b'\r\n')
            
            # 写入文件内容
            for key, file_info in files.items():
                content = file_info.get('content', b'')
                if isinstance(content, str):
                    content = content.encode('utf-8')
                tmp.write(content)
                tmp.write(b'\r\n')
            
            # 写入结束boundary
            tmp.write(data_parts[-2].encode('utf-8') + b'\r\n')
            tmp.write(data_parts[-1].encode('utf-8'))
            tmp.flush()
            
            # 读取文件内容
            with open(tmp.name, 'rb') as f:
                body = f.read()
        
        os.unlink(tmp.name)
    
    # 设置headers
    req_headers = headers()
    req_headers['Content-Type'] = f'multipart/form-data; boundary={boundary}'
    req_headers['Content-Length'] = str(len(body))
    
    req = urllib.request.Request(BASE_URL + path, data=body, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode('utf-8', errors='replace'))


def create_functional_cases(payloads, attach_file_id=None):
    results = []
    for idx, item in enumerate(payloads):
        # 处理附件
        if attach_file_id:
            relate = item.get('relateFileMetaIds') or []
            if isinstance(relate, str):
                try:
                    relate = json.loads(relate)
                except:
                    relate = []
            # 去重
            if attach_file_id not in relate:
                relate.append(attach_file_id)
            item['relateFileMetaIds'] = relate
        # 确保数据格式正确
        # 1. 确保tags是数组，不是字符串
        if 'tags' in item and isinstance(item['tags'], str):
            try:
                item['tags'] = json.loads(item['tags'])
            except:
                item['tags'] = []
        
        # 2. 确保customFields是数组，不是字符串
        if 'customFields' in item and isinstance(item['customFields'], str):
            try:
                item['customFields'] = json.loads(item['customFields'])
            except:
                item['customFields'] = []
        
        # 检查projectId
        if not item.get('projectId'):
            raise ValueError(f"元素 {idx} 缺少 projectId")
        
        # 3. 确保有正确的templateId
        if not item.get('templateId'):
            # 尝试从环境变量获取默认templateId
            import os
            template_id = os.environ.get('METERSPHERE_DEFAULT_TEMPLATE_ID')
            if template_id:
                item['templateId'] = template_id
            else:
                raise ValueError(f"元素 {idx} 缺少 templateId，且未设置 METERSPHERE_DEFAULT_TEMPLATE_ID")
        

        
        # 4. 使用curl发送multipart/form-data请求
        try:
            import tempfile
            import subprocess
            
            # 创建临时文件保存JSON数据
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(item, f, ensure_ascii=False)
                json_file = f.name
            
            # 生成签名
            plain = f'{AK}|{uuid.uuid4()}|{int(time.time()*1000)}'
            p = subprocess.run([
                'openssl', 'enc', '-aes-128-cbc', '-K', SK.encode().hex(), '-iv', AK.encode().hex(), '-base64', '-A', '-nosalt'
            ], input=plain.encode(), capture_output=True, check=True)
            signature = p.stdout.decode().strip()
            
            # 构建curl命令
            curl_cmd = [
                'curl', '-X', 'POST',
                '-H', f'accessKey: {AK}',
                '-H', f'signature: {signature}',
                '-F', f'request=@{json_file};type=application/json',
                f'{BASE_URL}{FUNCTIONAL_CASE_CREATE_PATH}'
            ]
            
            # 执行curl命令
            result = subprocess.run(curl_cmd, capture_output=True, text=True, timeout=30)
            
            # 解析响应
            if result.stdout:
                response_data = json.loads(result.stdout)
                results.append(response_data)
            else:
                results.append({'error': 'No response', 'data': None})
            
            # 清理临时文件
            import os
            os.unlink(json_file)
            
        except Exception as e:
            print(f"创建用例失败: {e}", file=sys.stderr)
            results.append({'error': str(e), 'data': None})
    
    return results


def create_api_definitions_and_cases(bundle):
    results = []
    for definition, case_list in zip(bundle.get('definitions', []), bundle.get('cases', [])):
        r = request_json('POST', '/api/definition/add', definition)
        created = r.get('data') or {}
        api_id = created.get('id') if isinstance(created, dict) else None
        case_results = []
        if api_id:
            for case_tpl in case_list:
                case_body = copy.deepcopy(case_tpl)
                case_body['projectId'] = definition['projectId']
                case_body['apiDefinitionId'] = api_id
                case_body['request']['moduleId'] = definition['moduleId']
                case_results.append(request_json('POST', '/api/case/add', case_body))
        results.append({'definition': r, 'cases': case_results})
    return results


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        die('用法: ms_batch.py functional-cases <json-file> [--attach-file-id <fileMetadataId>] | api-import <json-file>')
    mode = args[0]
    attach_file_id = None
    file_path = None
    i = 1
    while i < len(args):
        if args[i] == '--attach-file-id':
            if i + 1 >= len(args):
                die('用法: ms_batch.py functional-cases <json-file> [--attach-file-id <fileMetadataId>] | api-import <json-file>')
            attach_file_id = args[i + 1]
            i += 2
            continue
        elif args[i].startswith('--attach-file-id='):
            attach_file_id = args[i].split('=', 1)[1]
            i += 1
            continue
        else:
            if file_path is None:
                file_path = args[i]
            i += 1
    if file_path is None:
        die('用法: ms_batch.py functional-cases <json-file> [--attach-file-id <fileMetadataId>] | api-import <json-file>')
    
    # 支持从标准输入读取（当文件路径为"-"时）
    if file_path == '-':
        payload = json.loads(sys.stdin.read())
    else:
        payload = json.loads(Path(file_path).read_text(encoding='utf-8'))
    
    try:
        if mode == 'functional-cases':
            res = create_functional_cases(payload, attach_file_id=attach_file_id)
            print(json.dumps(res, ensure_ascii=False, indent=2))
            for r in res:
                if isinstance(r, dict) and r.get('error'):
                    sys.exit(1)
        elif mode == 'api-import':
            res = create_api_definitions_and_cases(payload)
            print(json.dumps(res, ensure_ascii=False, indent=2))
            for r in res:
                if isinstance(r, dict) and r.get('error'):
                    sys.exit(1)
        else:
            die('未知模式')
    except ValueError as e:
        die(str(e))

if __name__ == '__main__':
    main()
