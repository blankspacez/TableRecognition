## Extract Tables from PDF
输入： PDF 文件  
输出：一个 ZIP 格式的压缩包，其中包含从该 PDF 文件中提取的所有表格，每个表格以 XLSX 格式存储。

## 通过web访问
http://xxx.xx.xx.xxx:3300

## 通过requests库调用接口

```py
import requests

# 定义上传文件的路径
file_path = 'xxx/xxx/xxx.pdf'

# 构建 HTTP 请求
url = 'http://xxx.xx.xx.xxx:3300/upload'
files = {'file': open(file_path, 'rb')}

# 发送 POST 请求
response = requests.post(url, files=files)

# 保存结果文件
if response.status_code == 200:
    # 定义保存文件的路径
    save_path= 'xxx/xxx/xxx.zip'   
    with open(save_path, 'wb') as result_file:
        result_file.write(response.content)
    print(f'结果文件已保存到{save_path}')
else:
    print('请求失败:', response.text)
```