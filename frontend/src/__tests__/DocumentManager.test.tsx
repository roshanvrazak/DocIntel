import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { DocumentManager } from '../components/DocumentManager'
import { apiClient } from '../services/api'

vi.mock('../services/api', () => ({
  apiClient: {
    get: vi.fn(),
    delete: vi.fn(),
    post: vi.fn(),
  },
}))

const mockDocs = [
  { id: 'doc-1', filename: 'report.pdf', status: 'ready', created_at: '2024-01-15T10:00:00Z' },
  { id: 'doc-2', filename: 'research.pdf', status: 'processing', created_at: '2024-01-16T11:00:00Z' },
  { id: 'doc-3', filename: 'summary.pdf', status: 'error', created_at: '2024-01-17T12:00:00Z' },
]

function mockListResponse(docs = mockDocs, total = docs.length) {
  return Promise.resolve({ data: { documents: docs, total } })
}

describe('DocumentManager', () => {
  beforeEach(() => {
    vi.mocked(apiClient.get).mockReturnValue(mockListResponse() as any)
  })

  afterEach(() => {
    vi.clearAllMocks()
  })

  // ---------------------------------------------------------------------------
  // List rendering
  // ---------------------------------------------------------------------------

  it('renders the document library heading', async () => {
    render(<DocumentManager />)
    expect(screen.getByText(/document library/i)).toBeInTheDocument()
  })

  it('shows a loading spinner while fetching', () => {
    // Never resolve — stays in loading state
    vi.mocked(apiClient.get).mockReturnValue(new Promise(() => {}) as any)
    render(<DocumentManager />)
    // The Loader2 spinner renders inside a flex container
    const spinners = document.querySelectorAll('.animate-spin')
    expect(spinners.length).toBeGreaterThan(0)
  })

  it('renders all fetched document filenames', async () => {
    render(<DocumentManager />)
    await waitFor(() => {
      expect(screen.getByText('report.pdf')).toBeInTheDocument()
      expect(screen.getByText('research.pdf')).toBeInTheDocument()
      expect(screen.getByText('summary.pdf')).toBeInTheDocument()
    })
  })

  it('shows "No documents yet" when list is empty', async () => {
    vi.mocked(apiClient.get).mockReturnValue(
      Promise.resolve({ data: { documents: [], total: 0 } }) as any
    )
    render(<DocumentManager />)
    await waitFor(() => {
      expect(screen.getByText(/no documents yet/i)).toBeInTheDocument()
    })
  })

  it('applies correct status badge colours', async () => {
    render(<DocumentManager />)
    await waitFor(() => screen.getByText('report.pdf'))

    // Find all status badges by their text content
    const readyBadge = screen.getByText('ready')
    const processingBadge = screen.getByText('processing')
    const errorBadge = screen.getByText('error')

    expect(readyBadge.className).toContain('green')
    expect(errorBadge.className).toContain('red')
    expect(processingBadge.className).toContain('blue')
  })

  // ---------------------------------------------------------------------------
  // Delete
  // ---------------------------------------------------------------------------

  it('prompts for confirmation before deleting', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(<DocumentManager />)
    await waitFor(() => screen.getByText('report.pdf'))

    const deleteButtons = screen.getAllByLabelText(/delete/i)
    fireEvent.click(deleteButtons[0])

    expect(confirmSpy).toHaveBeenCalledOnce()
    expect(apiClient.delete).not.toHaveBeenCalled()
    confirmSpy.mockRestore()
  })

  it('calls DELETE endpoint and refreshes list on confirmation', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(apiClient.delete).mockResolvedValue({} as any)
    const onChangeMock = vi.fn()

    render(<DocumentManager onDocumentsChange={onChangeMock} />)
    await waitFor(() => screen.getByText('report.pdf'))

    const deleteButtons = screen.getAllByLabelText(/delete/i)
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(apiClient.delete).toHaveBeenCalledWith('/api/documents/doc-1')
      expect(onChangeMock).toHaveBeenCalledOnce()
      // List was re-fetched after delete
      expect(apiClient.get).toHaveBeenCalledTimes(2)
    })
  })

  it('shows error banner when delete fails', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    vi.mocked(apiClient.delete).mockRejectedValue(new Error('server error'))

    render(<DocumentManager />)
    await waitFor(() => screen.getByText('report.pdf'))

    const deleteButtons = screen.getAllByLabelText(/delete/i)
    fireEvent.click(deleteButtons[0])

    await waitFor(() => {
      expect(screen.getByText(/failed to delete/i)).toBeInTheDocument()
    })
  })

  // ---------------------------------------------------------------------------
  // Reprocess
  // ---------------------------------------------------------------------------

  it('calls reprocess endpoint on button click', async () => {
    vi.mocked(apiClient.post).mockResolvedValue({} as any)

    render(<DocumentManager />)
    await waitFor(() => screen.getByText('report.pdf'))

    const reprocessButtons = screen.getAllByLabelText(/reprocess/i)
    fireEvent.click(reprocessButtons[0])

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/api/documents/doc-1/reprocess')
    })
  })

  it('shows error banner with API detail when reprocess fails', async () => {
    vi.mocked(apiClient.post).mockRejectedValue({
      response: { data: { detail: 'Document is already processing' } },
    })

    render(<DocumentManager />)
    await waitFor(() => screen.getByText('report.pdf'))

    const reprocessButtons = screen.getAllByLabelText(/reprocess/i)
    fireEvent.click(reprocessButtons[0])

    await waitFor(() => {
      expect(screen.getByText('Document is already processing')).toBeInTheDocument()
    })
  })

  // ---------------------------------------------------------------------------
  // Pagination
  // ---------------------------------------------------------------------------

  it('hides pagination when total fits on one page', async () => {
    render(<DocumentManager />)
    await waitFor(() => screen.getByText('report.pdf'))
    // 3 docs, limit=10 — no pagination controls
    expect(screen.queryByText('Prev')).not.toBeInTheDocument()
    expect(screen.queryByText('Next')).not.toBeInTheDocument()
  })

  it('shows pagination when total exceeds page limit', async () => {
    // Return 11 total but only first page of docs
    vi.mocked(apiClient.get).mockReturnValue(
      Promise.resolve({ data: { documents: mockDocs, total: 11 } }) as any
    )
    render(<DocumentManager />)
    await waitFor(() => screen.getByText('report.pdf'))
    expect(screen.getByText('Prev')).toBeInTheDocument()
    expect(screen.getByText('Next')).toBeInTheDocument()
  })

  it('prev button is disabled on first page', async () => {
    vi.mocked(apiClient.get).mockReturnValue(
      Promise.resolve({ data: { documents: mockDocs, total: 11 } }) as any
    )
    render(<DocumentManager />)
    await waitFor(() => screen.getByText('Prev'))

    const prevButton = screen.getByText('Prev').closest('button')!
    expect(prevButton).toBeDisabled()
  })

  // ---------------------------------------------------------------------------
  // Refresh
  // ---------------------------------------------------------------------------

  it('refresh button re-fetches the document list', async () => {
    render(<DocumentManager />)
    await waitFor(() => screen.getByText('report.pdf'))

    const refreshButton = screen.getByLabelText('Refresh document list')
    fireEvent.click(refreshButton)

    await waitFor(() => {
      expect(apiClient.get).toHaveBeenCalledTimes(2)
    })
  })
})
