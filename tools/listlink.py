from collections.abc import Generator
from typing import Any
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from webdriver_manager.chrome import ChromeDriverManager
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class ListLinkTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage]:
        # 获取参数
        listurl = tool_parameters.get('listurl', '')
        boxclass = tool_parameters.get('boxclass', '')
        subclass = tool_parameters.get('subclass', '')
        aclass = tool_parameters.get('aclass', '')
        link = tool_parameters.get('link', '')
        blockurl = tool_parameters.get('blockurl', '')
        use_browser = tool_parameters.get('use_browser', False)
        
        if not listurl or not boxclass:
            yield self.create_json_message({
                "error": "listurl and boxclass are required parameters"
            })
            return
        
        try:
            # 根据参数选择获取HTML内容的方式
            if use_browser:
                if not SELENIUM_AVAILABLE:
                    yield self.create_json_message({
                        "error": "使用浏览器模式需要安装selenium库，请运行: pip install selenium"
                    })
                    return
                html_content = self._get_html_content_with_browser(listurl)
            else:
                html_content = self._get_html_content(listurl)
            
            if not html_content:
                yield self.create_json_message({
                    "error": "Failed to fetch HTML content from the URL"
                })
                return
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取链接
            links = self._extract_links(soup, boxclass, subclass, aclass, link, listurl, blockurl)
            
            # 输出结果
            yield self.create_json_message({
                "links": links,
                "count": len(links)
            })
            
        except Exception as e:
            yield self.create_json_message({
                "error": f"An error occurred: {str(e)}"
            })
    
    def _get_html_content(self, url):
        """获取HTML内容，支持多种编码"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            # 尝试多种编码方式
            encodings = ['utf-8', 'gb2312', 'gbk', 'latin1']
            for encoding in encodings:
                try:
                    html_content = response.content.decode(encoding)
                    return html_content
                except UnicodeDecodeError:
                    continue
            
            # 如果所有编码都失败，使用默认的response.text
            return response.text
            
        except Exception as e:
            return None
    
    def _get_html_content_with_browser(self, url):
        """使用无头浏览器获取动态渲染的HTML内容"""
        if not SELENIUM_AVAILABLE:
            return None
        
        driver = None
        try:
            # 配置Chrome选项
            chrome_options = Options()
            chrome_options.add_argument('--headless')  # 无头模式
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36')
            
            # 创建WebDriver实例（自动下载和管理ChromeDriver）
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            driver.set_page_load_timeout(30)
            
            # 访问页面
            driver.get(url)
            
            # 等待页面加载完成（等待body元素出现）
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # 额外等待JavaScript执行
            time.sleep(3)
            
            # 获取渲染后的HTML
            html_content = driver.page_source
            return html_content
            
        except Exception as e:
            print(f"浏览器获取内容失败: {str(e)}")
            return None
        finally:
            if driver:
                driver.quit()
    
    def _extract_links(self, soup, boxclass, subclass, aclass, base_url, original_url, blockurl=''):
        """提取链接"""
        links = []
        
        # 解析父类名
        box_classes = self._parse_class_names(boxclass)
        
        # 查找父容器
        parent_elements = self._find_elements_by_classes(soup, box_classes)
        
        if not parent_elements:
            return links
        
        for parent_element in parent_elements:
            if aclass:
                # 如果指定了aclass，直接查找该类的a标签
                a_classes = self._parse_class_names(aclass)
                a_elements = self._find_elements_by_classes(parent_element, a_classes, tag='a')
            elif subclass:
                # 如果指定了subclass，先找子元素，再找其中的a标签
                if self._is_html_tag(subclass):
                    # 如果是HTML标签格式（如<li>、<span>等），直接按标签名查找
                    tag_name = self._extract_tag_name(subclass)
                    sub_elements = parent_element.find_all(tag_name)
                else:
                    # 如果是CSS类名，按类名查找
                    sub_classes = self._parse_class_names(subclass)
                    sub_elements = self._find_elements_by_classes(parent_element, sub_classes)
                
                a_elements = []
                for sub_element in sub_elements:
                    a_elements.extend(sub_element.find_all('a', href=True))
            else:
                # 如果没有指定subclass和aclass，直接查找父容器中的所有a标签
                a_elements = parent_element.find_all('a', href=True)
            
            # 提取href并处理URL
            for a_element in a_elements:
                href = a_element.get('href')
                if href:
                    # 处理相对链接
                    if base_url:
                        # 如果提供了base_url，使用它来拼接
                        if href.startswith('/'):
                            full_url = base_url.rstrip('/') + href
                        elif href.startswith('http'):
                            full_url = href
                        else:
                            full_url = base_url.rstrip('/') + '/' + href
                    else:
                        # 使用原始URL作为基础URL
                        full_url = urljoin(original_url, href)
                    
                    # 过滤链接
                    if self._should_block_url(full_url, blockurl):
                        continue
                    
                    if full_url not in links:
                        links.append(full_url)
        
        return links
    
    def _parse_class_names(self, class_names):
        """解析类名字符串，支持空格和逗号分隔"""
        if not class_names:
            return []
        
        # 先按逗号分割，再按空格分割
        class_list = []
        parts = class_names.replace(',', ' ').split()
        for part in parts:
            if part.strip():
                class_list.append(part.strip())
        return class_list
    
    def _find_elements_by_classes(self, soup, class_list, tag=None):
        """根据类名列表查找元素"""
        elements = []
        
        if not class_list:
            return elements
        
        # 策略1：精确匹配所有类名
        if len(class_list) > 1:
            selector = '.' + '.'.join(class_list)
            if tag:
                selector = tag + selector
            found_elements = soup.select(selector)
            elements.extend(found_elements)
        
        # 策略2：单个类名匹配
        if not elements:
            for class_name in class_list:
                if tag:
                    found_elements = soup.find_all(tag, class_=class_name)
                else:
                    found_elements = soup.find_all(class_=class_name)
                elements.extend(found_elements)
        
        # 策略3：包含任意一个类名的元素（模糊匹配）
        if not elements:
            for class_name in class_list:
                if tag:
                    found_elements = soup.find_all(tag, class_=re.compile(class_name))
                else:
                    found_elements = soup.find_all(class_=re.compile(class_name))
                elements.extend(found_elements)
        
        # 去重
        unique_elements = []
        for element in elements:
            if element not in unique_elements:
                unique_elements.append(element)
        
        return unique_elements
    
    def _is_html_tag(self, text):
        """判断输入是否为HTML标签格式（如<li>、<span>等）"""
        import re
        return bool(re.match(r'^<[a-zA-Z][a-zA-Z0-9]*>$', text.strip()))
    
    def _extract_tag_name(self, tag_text):
        """从HTML标签格式中提取标签名（如从<li>提取li）"""
        import re
        match = re.match(r'^<([a-zA-Z][a-zA-Z0-9]*)>$', tag_text.strip())
        return match.group(1) if match else None
    
    def _should_block_url(self, url, blockurl):
        """判断链接是否应该被屏蔽"""
        # 自动屏蔽空链接和javascript链接
        if not url or url.strip() == '' or url.strip() == '#' or url.lower().startswith('javascript:'):
            return True
        
        # 如果没有设置屏蔽关键词，则不屏蔽
        if not blockurl or not blockurl.strip():
            return False
        
        # 解析屏蔽关键词
        block_keywords = self._parse_class_names(blockurl)
        
        # 检查URL是否包含任一屏蔽关键词
        for keyword in block_keywords:
            if keyword and keyword.strip() and keyword.strip().lower() in url.lower():
                return True
        
        return False
