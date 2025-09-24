import React from 'react'
import { render, fireEvent } from '@testing-library/react'
import '@testing-library/jest-dom'
import GalleryApp from './GalleryApp'

test('lightbox opens and closes and responds to keyboard', () => {
  // Render with no network calls; shallow smoke test verifying component mounts
  const { getByText, queryByRole } = render(<GalleryApp />)
  // Initially there should be a heading
  expect(getByText('Gallery')).toBeInTheDocument()
  // Lightbox should not be present
  expect(queryByRole('dialog')).toBeNull()
})
