import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import NumericInput from './NumericInput';

describe('NumericInput', () => {
  const mockOnChange = jest.fn();
  const mockOnValidate = jest.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
    mockOnValidate.mockClear();
  });

  test('renders with label and tooltip', () => {
    render(<NumericInput label="Test Label" tooltip="Test Tooltip" value="10" onChange={() => {}} />);
    expect(screen.getByLabelText(/Test Label/i)).toBeInTheDocument();
    expect(screen.getByTitle(/Test Tooltip/i)).toBeInTheDocument();
  });

  test('displays initial value', () => {
    render(<NumericInput label="Test Label" value="123" onChange={() => {}} />);
    expect(screen.getByRole('spinbutton')).toHaveValue(123);
  });

  test('calls onChange and onValidate when value changes', () => {
    render(
      <NumericInput
        label="Test Label"
        value="10"
        onChange={mockOnChange}
        onValidate={mockOnValidate}
      />
    );
    const input = screen.getByRole('spinbutton');
    fireEvent.change(input, { target: { value: '20' } });
    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnValidate).toHaveBeenCalledTimes(1);
    expect(mockOnValidate).toHaveBeenCalledWith('20');
  });

  test('displays error message', () => {
    render(<NumericInput label="Test Label" value="10" onChange={() => {}} error="Invalid input" />);
    expect(screen.getByText('Invalid input')).toBeInTheDocument();
    expect(screen.getByText('Invalid input')).toHaveStyle('color: red');
  });

  test('is disabled when disabled prop is true', () => {
    render(<NumericInput label="Test Label" value="10" onChange={() => {}} disabled={true} />);
    expect(screen.getByRole('spinbutton')).toBeDisabled();
  });
});
