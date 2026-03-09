import unittest

from app.services.job_fetcher import JobFetcher


class TestJobFetcher(unittest.TestCase):
    def test_parse_html_filters_placeholder_and_uses_title_fallback(self):
        html = """
        <html>
          <head><title>高级后端工程师-某科技公司-北京_30-45K</title></head>
          <body>
            <h1>职位名称</h1>
            <div class='company-name'>公司名称</div>
            <div class='salary'>薪资范围</div>
            <div class='job-area'>工作地点</div>
            <div>职位描述：负责核心系统研发与性能优化，参与架构设计与代码评审。</div>
          </body>
        </html>
        """
        info = JobFetcher.parse_html("https://www.zhipin.com/job_detail/xxx", html)
        self.assertEqual(info.title, "高级后端工程师")
        self.assertEqual(info.company, "某科技公司")
        self.assertEqual(info.salary, None)
        self.assertEqual(info.location, None)
        self.assertTrue(any("负责核心系统研发" in x for x in info.responsibilities))

    def test_parse_text_for_ocr_output(self):
        text = """
        岗位职责：
        1. 负责核心后端服务开发与性能优化
        2. 参与系统架构设计
        任职要求：
        1. 熟悉 Python/FastAPI
        工作地点：北京朝阳
        薪资 30-45K
        """
        info = JobFetcher.parse_text(
            "https://www.zhipin.com/job_detail/xxx",
            text,
            page_title="高级后端工程师-某科技公司-北京_30-45K",
        )
        self.assertEqual(info.title, "高级后端工程师")
        self.assertEqual(info.company, "某科技公司")
        self.assertEqual(info.salary, "30-45K")
        self.assertEqual(info.location, "北京朝阳")
        self.assertTrue(info.responsibilities)
        self.assertTrue(info.requirements)


if __name__ == "__main__":
    unittest.main()
