import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { ActionPanel, ActionType } from '../components/ActionPanel'
import { UploadingFile } from '../types'

function makeDoc(id: string, name: string): UploadingFile {
  return {
    id,
    localId: id,
    file: new File(['content'], name, { type: 'application/pdf' }),
    status: 'ready',
    progress: 100,
  }
}

const defaultProps = {
  documents: [],
  selectedAction: 'qa' as ActionType,
  onActionChange: vi.fn(),
  selectedDocIds: [],
  onDocSelectionChange: vi.fn(),
}

describe('ActionPanel', () => {
  it('renders all action buttons', () => {
    render(<ActionPanel {...defaultProps} />)
    expect(screen.getByLabelText('Select Summarize action')).toBeInTheDocument()
    expect(screen.getByLabelText('Select Compare action')).toBeInTheDocument()
    expect(screen.getByLabelText('Select Q&A action')).toBeInTheDocument()
    expect(screen.getByLabelText('Select Extract action')).toBeInTheDocument()
    expect(screen.getByLabelText('Select Semantic Search action')).toBeInTheDocument()
  })

  it('marks the selected action as pressed', () => {
    render(<ActionPanel {...defaultProps} selectedAction="compare" />)
    const compareBtn = screen.getByLabelText('Select Compare action')
    expect(compareBtn).toHaveAttribute('aria-pressed', 'true')
    const qaBtn = screen.getByLabelText('Select Q&A action')
    expect(qaBtn).toHaveAttribute('aria-pressed', 'false')
  })

  it('calls onActionChange when an action is clicked', () => {
    const onActionChange = vi.fn()
    render(<ActionPanel {...defaultProps} onActionChange={onActionChange} />)
    fireEvent.click(screen.getByLabelText('Select Summarize action'))
    expect(onActionChange).toHaveBeenCalledWith('summarize')
  })

  it('shows empty state when no documents are ready', () => {
    render(<ActionPanel {...defaultProps} documents={[]} />)
    expect(screen.getByText(/no processed documents/i)).toBeInTheDocument()
  })

  it('renders ready documents as selectable buttons', () => {
    const docs = [makeDoc('abc', 'paper_a.pdf'), makeDoc('def', 'paper_b.pdf')]
    render(<ActionPanel {...defaultProps} documents={docs} />)
    expect(screen.getByLabelText('Toggle selection for paper_a.pdf')).toBeInTheDocument()
    expect(screen.getByLabelText('Toggle selection for paper_b.pdf')).toBeInTheDocument()
  })

  it('calls onDocSelectionChange when a document is toggled on', () => {
    const onDocSelectionChange = vi.fn()
    const docs = [makeDoc('abc', 'paper_a.pdf')]
    render(
      <ActionPanel
        {...defaultProps}
        documents={docs}
        selectedDocIds={[]}
        onDocSelectionChange={onDocSelectionChange}
      />
    )
    fireEvent.click(screen.getByLabelText('Toggle selection for paper_a.pdf'))
    expect(onDocSelectionChange).toHaveBeenCalledWith(['abc'])
  })

  it('calls onDocSelectionChange when a selected document is toggled off', () => {
    const onDocSelectionChange = vi.fn()
    const docs = [makeDoc('abc', 'paper_a.pdf')]
    render(
      <ActionPanel
        {...defaultProps}
        documents={docs}
        selectedDocIds={['abc']}
        onDocSelectionChange={onDocSelectionChange}
      />
    )
    fireEvent.click(screen.getByLabelText('Toggle selection for paper_a.pdf'))
    expect(onDocSelectionChange).toHaveBeenCalledWith([])
  })

  it('select all selects all ready document IDs', () => {
    const onDocSelectionChange = vi.fn()
    const docs = [makeDoc('abc', 'a.pdf'), makeDoc('def', 'b.pdf')]
    render(
      <ActionPanel
        {...defaultProps}
        documents={docs}
        selectedDocIds={[]}
        onDocSelectionChange={onDocSelectionChange}
      />
    )
    fireEvent.click(screen.getByLabelText('Select all documents'))
    expect(onDocSelectionChange).toHaveBeenCalledWith(['abc', 'def'])
  })

  it('clear button deselects all documents', () => {
    const onDocSelectionChange = vi.fn()
    const docs = [makeDoc('abc', 'a.pdf')]
    render(
      <ActionPanel
        {...defaultProps}
        documents={docs}
        selectedDocIds={['abc']}
        onDocSelectionChange={onDocSelectionChange}
      />
    )
    fireEvent.click(screen.getByLabelText('Clear document selection'))
    expect(onDocSelectionChange).toHaveBeenCalledWith([])
  })

  it('select all is disabled when no documents are ready', () => {
    render(<ActionPanel {...defaultProps} documents={[]} />)
    expect(screen.getByLabelText('Select all documents')).toBeDisabled()
  })

  it('does not render processing documents as selectable', () => {
    const processingDoc: UploadingFile = {
      id: 'xyz',
      localId: 'xyz',
      file: new File([''], 'processing.pdf'),
      status: 'embedding',
      progress: 50,
    }
    render(<ActionPanel {...defaultProps} documents={[processingDoc]} />)
    expect(screen.queryByLabelText('Toggle selection for processing.pdf')).not.toBeInTheDocument()
  })
})
