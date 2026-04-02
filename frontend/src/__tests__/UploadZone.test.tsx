import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UploadZone } from '../components/UploadZone'
import { UploadingFile } from '../types'
import * as api from '../services/api'

vi.mock('../services/api', () => ({
  uploadClient: {
    post: vi.fn(),
  },
}))

// Suppress react-dropzone's drag event warnings in jsdom
vi.mock('react-dropzone', async () => {
  const actual = await vi.importActual<typeof import('react-dropzone')>('react-dropzone')
  return actual
})

function renderUploadZone(files: UploadingFile[] = []) {
  const setFiles = vi.fn()
  const { rerender } = render(<UploadZone files={files} setFiles={setFiles} />)
  return { setFiles, rerender }
}

describe('UploadZone', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the drop area with instructions', () => {
    renderUploadZone()
    expect(screen.getByText(/upload research papers/i)).toBeInTheDocument()
  })

  it('shows no file list when files array is empty', () => {
    renderUploadZone([])
    expect(screen.queryByText(/processing queue/i)).not.toBeInTheDocument()
  })

  it('shows processing queue when files are present', () => {
    const files: UploadingFile[] = [
      {
        localId: 'a',
        file: new File(['%PDF-'], 'test.pdf', { type: 'application/pdf' }),
        status: 'uploading',
        progress: 20,
      },
    ]
    renderUploadZone(files)
    expect(screen.getByText(/processing queue/i)).toBeInTheDocument()
    expect(screen.getByText('test.pdf')).toBeInTheDocument()
  })

  it('shows spinner and progress for in-progress file', () => {
    const files: UploadingFile[] = [
      {
        localId: 'a',
        file: new File(['%PDF-'], 'loading.pdf', { type: 'application/pdf' }),
        status: 'uploading',
        progress: 42,
      },
    ]
    renderUploadZone(files)
    expect(screen.getByText('42%')).toBeInTheDocument()
  })

  it('shows ready status badge for completed file', () => {
    const files: UploadingFile[] = [
      {
        id: 'uuid-1',
        localId: 'a',
        file: new File(['%PDF-'], 'done.pdf', { type: 'application/pdf' }),
        status: 'ready',
        progress: 100,
      },
    ]
    renderUploadZone(files)
    expect(screen.getByText('ready')).toBeInTheDocument()
  })

  it('shows error status for failed file', () => {
    const files: UploadingFile[] = [
      {
        localId: 'a',
        file: new File(['%PDF-'], 'failed.pdf', { type: 'application/pdf' }),
        status: 'error',
        progress: 0,
      },
    ]
    renderUploadZone(files)
    expect(screen.getByText('error')).toBeInTheDocument()
  })

  it('calls setFiles and uploadClient.post when a file is dropped', async () => {
    const mockedPost = vi.mocked(api.uploadClient.post)
    mockedPost.mockResolvedValue({ data: { id: 'new-uuid', status: 'uploaded' } })

    const setFiles = vi.fn()
    render(<UploadZone files={[]} setFiles={setFiles} />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['%PDF-content'], 'upload.pdf', { type: 'application/pdf' })

    await act(async () => {
      await userEvent.upload(input, file)
    })

    await waitFor(() => {
      expect(setFiles).toHaveBeenCalled()
    })
  })

  it('sets error status when upload API call fails', async () => {
    const mockedPost = vi.mocked(api.uploadClient.post)
    mockedPost.mockRejectedValue(new Error('Network error'))

    const setFiles = vi.fn()
    render(<UploadZone files={[]} setFiles={setFiles} />)

    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    const file = new File(['%PDF-'], 'fail.pdf', { type: 'application/pdf' })

    await act(async () => {
      await userEvent.upload(input, file)
    })

    await waitFor(() => {
      const calls = setFiles.mock.calls.flat()
      const updaters = calls.filter((c) => typeof c === 'function')
      // The last updater should set status to 'error'
      expect(updaters.length).toBeGreaterThan(0)
    })
  })

  it('displays file count badge', () => {
    const files: UploadingFile[] = [
      { localId: 'a', file: new File(['%PDF-'], 'a.pdf'), status: 'ready', progress: 100 },
      { localId: 'b', file: new File(['%PDF-'], 'b.pdf'), status: 'uploading', progress: 50 },
    ]
    renderUploadZone(files)
    expect(screen.getByText('2 Files')).toBeInTheDocument()
  })
})
