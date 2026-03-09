import { useState } from 'react'
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export default function App() {
  const [file, setFile] = useState(null)
  const [jobUrl, setJobUrl] = useState('')
  const [jobPreview, setJobPreview] = useState(null)
  const [aiProvider, setAiProvider] = useState('mock')
  const [aiApiKey, setAiApiKey] = useState('')
  const [aiModel, setAiModel] = useState('')
  const [aiBaseUrl, setAiBaseUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [previewing, setPreviewing] = useState(false)
  const [result, setResult] = useState('')
  const [message, setMessage] = useState('')

  const handlePreviewJD = async () => {
    if (!jobUrl) {
      setMessage('请先填写岗位链接。')
      return
    }
    const formData = new FormData()
    formData.append('job_url', jobUrl)
    setPreviewing(true)
    setMessage('')
    try {
      const { data } = await axios.post(`${API_BASE}/api/job-preview`, formData)
      setJobPreview(data)
    } catch (error) {
      setMessage(error?.response?.data?.detail || 'JD预览失败，请稍后重试。')
    } finally {
      setPreviewing(false)
    }
  }

  const handleOptimize = async () => {
    if (!file || !jobUrl) {
      setMessage('请上传简历并填写岗位链接。')
      return
    }

    const formData = new FormData()
    formData.append('resume', file)
    formData.append('job_url', jobUrl)
    formData.append('ai_provider', aiProvider)
    formData.append('ai_api_key', aiApiKey)
    formData.append('ai_model', aiModel)
    formData.append('ai_base_url', aiBaseUrl)

    setLoading(true)
    setMessage('')
    try {
      const { data } = await axios.post(`${API_BASE}/api/optimize`, formData)
      setResult(data.optimized_resume_markdown)
      setJobPreview(data.job_info)
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
        <button onClick={handlePreviewJD} disabled={previewing}>
          {previewing ? '解析中...' : '预览JD'}
        </button>

        <label className="label">3) AI 模式</label>
        <select value={aiProvider} onChange={(e) => setAiProvider(e.target.value)}>
          <option value="mock">mock（无需 API Key）</option>
          <option value="doubao">doubao（需要 API Key）</option>
        </select>

        <label className="label">4) AI API Key（可选，本次请求生效）</label>
        <input
          type="password"
          placeholder="输入豆包 API Key"
          value={aiApiKey}
          onChange={(e) => setAiApiKey(e.target.value)}
        />

        <label className="label">5) AI 模型（可选）</label>
        <input
          type="text"
          placeholder="doubao-seed-1-6-250615"
          value={aiModel}
          onChange={(e) => setAiModel(e.target.value)}
        />

        <label className="label">6) AI Base URL（可选）</label>
        <input
          type="url"
          placeholder="https://ark.cn-beijing.volces.com/api/v3"
          value={aiBaseUrl}
          onChange={(e) => setAiBaseUrl(e.target.value)}
        />

        <button onClick={handleOptimize} disabled={loading}>
          {loading ? '处理中...' : '开始优化'}
        </button>
        {message && <p className="msg">{message}</p>}
      </section>

      <section className="panel">
        <h2>岗位JD预览</h2>
        <pre>{jobPreview ? JSON.stringify(jobPreview, null, 2) : '暂无岗位预览，点击“预览JD”后查看。'}</pre>
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
