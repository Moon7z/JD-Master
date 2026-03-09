import { useState } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function App() {
  const [file, setFile] = useState(null)
  const [jobUrl, setJobUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [result, setResult] = useState('')
  const [message, setMessage] = useState('')

  const handleOptimize = async () => {
    if (!file || !jobUrl) {
      setMessage('请上传简历并填写岗位链接。')
      return
    }

    const formData = new FormData()
    formData.append('resume', file)
    formData.append('job_url', jobUrl)

    setLoading(true)
    setMessage('')
    try {
      const { data } = await axios.post(`${API_BASE}/api/optimize`, formData)
      setResult(data.optimized_resume_markdown)
    } catch (error) {
      setMessage(error?.response?.data?.detail || '优化失败，请稍后重试。')
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = async () => {
    if (!result) return
    const formData = new FormData()
    formData.append('content', result)

    const response = await axios.post(`${API_BASE}/api/export`, formData, {
      responseType: 'blob',
    })

    const blob = new Blob([response.data], {
      type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    })
    const url = window.URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'optimized_resume.docx'
    anchor.click()
    window.URL.revokeObjectURL(url)
  }

  return (
    <div className="container">
      <h1>JD Master 智能简历定向优化</h1>
      <p className="subtitle">上传简历 + Boss直聘链接，自动生成岗位定制版简历</p>

      <section className="panel">
        <label className="label">1) 上传简历（docx / pdf）</label>
        <input
          type="file"
          accept=".docx,.pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />

        <label className="label">2) 岗位链接（Boss直聘）</label>
        <input
          type="url"
          placeholder="https://www.zhipin.com/job_detail/..."
          value={jobUrl}
          onChange={(e) => setJobUrl(e.target.value)}
        />

        <button onClick={handleOptimize} disabled={loading}>
          {loading ? '处理中...' : '开始优化'}
        </button>
        {message && <p className="msg">{message}</p>}
      </section>

      <section className="panel">
        <div className="result-header">
          <h2>结果预览</h2>
          <button onClick={handleDownload} disabled={!result}>下载 DOCX</button>
        </div>
        <pre>{result || '暂无结果，点击“开始优化”后在这里查看。'}</pre>
      </section>
    </div>
  )
}
