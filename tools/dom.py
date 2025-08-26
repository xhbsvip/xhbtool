from collections.abc import Generator
from typing import Any
import requests
from bs4 import BeautifulSoup
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

class DomHtmlTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # 获取URL参数
        url = tool_parameters.get("URL", "")
        
        if not url:
            yield self.create_text_message("请提供有效的URL")
            return
        
        # 判断是否使用动态渲染模式
        use_dynamic_rendering = tool_parameters.get("use_dynamic_rendering", True)
            
        try:
            # 获取HTML内容
            if use_dynamic_rendering:
                # 使用Selenium获取动态渲染后的HTML内容
                html_content = self._get_dynamic_html(url)
            else:
                # 使用传统方式获取静态HTML内容
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10)
                response.raise_for_status()  # 如果请求不成功则抛出异常
                
                # 尝试多种编码方式解码HTML内容
                content = response.content
                encodings = ['utf-8', 'gb2312', 'gbk', 'latin1']
                
                for encoding in encodings:
                    try:
                        html_content = content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    # 如果所有编码都失败，使用默认的response.text
                    html_content = response.text
            
            # 解析HTML内容
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取网站标题
            title = soup.title.string if soup.title else ""
            
            # 提取关键词
            keywords = ""
            keywords_meta = soup.find('meta', attrs={'name': 'keywords'}) or soup.find('meta', attrs={'property': 'keywords'})
            if keywords_meta and keywords_meta.get('content'):
                keywords = keywords_meta.get('content')
            
            # 提取描述
            description = ""
            description_meta = soup.find('meta', attrs={'name': 'description'}) or soup.find('meta', attrs={'property': 'description'}) or soup.find('meta', attrs={'property': 'og:description'})
            if description_meta and description_meta.get('content'):
                description = description_meta.get('content')
            
            # 处理可能的编码问题
            # 尝试不同的编码方式，包括latin1和GB2312
            encodings = ['latin1', 'gb2312', 'gbk']
            
            if title:
                for encoding in encodings:
                    try:
                        title = title.encode(encoding).decode('utf-8')
                        break
                    except:
                        pass
            
            if keywords:
                for encoding in encodings:
                    try:
                        keywords = keywords.encode(encoding).decode('utf-8')
                        break
                    except:
                        pass
            
            if description:
                for encoding in encodings:
                    try:
                        description = description.encode(encoding).decode('utf-8')
                        break
                    except:
                        pass
            
            # 输出HTML结构到text
            yield self.create_text_message(html_content)
            
            # 单独输出每个变量
            yield self.create_variable_message("title", title)
            yield self.create_variable_message("keywords", keywords)
            yield self.create_variable_message("description", description)
            yield self.create_variable_message("URL", url)
            
        except requests.exceptions.RequestException as e:
            yield self.create_text_message(f"获取网页内容时出错: {str(e)}")
        except Exception as e:
            yield self.create_text_message(f"处理网页结构时出错: {str(e)}")
    
    def _get_dynamic_html(self, url):
        """使用Selenium获取动态渲染后的HTML内容"""
        # 配置Chrome选项
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 无头模式
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        # 禁用Google API服务，避免GCM错误
        chrome_options.add_argument("--disable-features=GCMChannelStatus")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument("--disable-background-networking")
        chrome_options.add_argument("--disable-sync")
        chrome_options.add_argument("--disable-default-apps")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_experimental_option('excludeSwitches', ['enable-logging'])  # 禁用日志输出
        
        try:
            # 初始化WebDriver
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # 设置页面加载超时
            driver.set_page_load_timeout(30)
            
            # 访问URL
            driver.get(url)
            
            # 等待页面加载完成（等待body元素可见）
            WebDriverWait(driver, 10).until(EC.presence_of_element_located(("tag name", "body")))
            
            # 额外等待一段时间，确保JavaScript执行完成
            time.sleep(2)
            
            # 获取页面源代码
            page_source = driver.page_source
            
            # 处理可能的编码问题
            encodings = ['utf-8', 'gb2312', 'gbk', 'latin1']
            html_content = page_source  # 默认值
            
            # 尝试不同的编码方式
            for encoding in encodings:
                try:
                    # 先尝试编码再解码，处理可能的编码问题
                    if isinstance(page_source, str):
                        html_content = page_source.encode(encoding).decode('utf-8')
                        break
                except:
                    continue
            
            # 关闭浏览器
            driver.quit()
            
            return html_content
        except Exception as e:
            raise Exception(f"动态渲染获取失败: {str(e)}")
    
    def _extract_structure(self, soup):
        """提取网页的DOM结构"""
        result = {}
        
        # 获取标题
        title = soup.title.string if soup.title else "无标题"
        result["title"] = title
        
        # 获取meta信息
        meta_tags = []
        for meta in soup.find_all('meta'):
            meta_info = {}
            for attr in meta.attrs:
                meta_info[attr] = meta[attr]
            meta_tags.append(meta_info)
        result["meta"] = meta_tags
        
        # 获取页面结构
        body_structure = self._parse_element(soup.body) if soup.body else {}
        result["body"] = body_structure
        
        return result
    
    def _parse_element(self, element, max_depth=3, current_depth=0):
        """递归解析HTML元素结构"""
        if current_depth > max_depth:
            return {"type": element.name, "truncated": True}
            
        result = {"type": element.name}
        
        # 获取元素属性
        if element.attrs:
            result["attributes"] = {}
            for attr, value in element.attrs.items():
                result["attributes"][attr] = value
        
        # 获取元素内容
        if element.string and element.string.strip():
            result["text"] = element.string.strip()
        
        # 递归处理子元素
        children = []
        for child in element.children:
            if child.name:  # 只处理有标签名的元素
                child_structure = self._parse_element(child, max_depth, current_depth + 1)
                children.append(child_structure)
        
        if children:
            result["children"] = children
            
        return result
