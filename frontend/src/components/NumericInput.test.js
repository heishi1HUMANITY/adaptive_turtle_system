import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import NumericInput from './NumericInput';

describe('NumericInput', () => {
  const mockOnChange = jest.fn();
  const mockOnValidate = jest.fn();
  const testId = "test-numeric-input"; // Define a test ID

  beforeEach(() => {
    mockOnChange.mockClear();
    mockOnValidate.mockClear();
  });

  test('renders with label and tooltip, and label is associated with input', () => {
    render(
      <NumericInput
        id={testId} // Pass id
        label="Test Label"
        tooltip="Test Tooltip"
        value="10"
        onChange={() => {}}
      />
    );
    // Check if the input is accessible via its label
    expect(screen.getByLabelText(/Test Label/i)).toBeInTheDocument();
    // Check if the input itself has the correct id
    expect(screen.getByRole('spinbutton', { name: /Test Label/i })).toHaveAttribute('id', testId);
    expect(screen.getByTitle(/Test Tooltip/i)).toBeInTheDocument();
  });

  test('displays initial value', () => {
    render(
      <NumericInput
        id={testId} // Pass id
        label="Test Label"
        value="123"
        onChange={() => {}}
      />
    );
    expect(screen.getByLabelText(/Test Label/i)).toHaveValue(123);
  });

  test('calls onChange and onValidate when value changes', () => {
    render(
      <NumericInput
        id={testId} // Pass id
        label="Test Label"
        value="10"
        onChange={mockOnChange}
        onValidate={mockOnValidate}
      />
    );
    const input = screen.getByLabelText(/Test Label/i);
    fireEvent.change(input, { target: { value: '20' } });
    expect(mockOnChange).toHaveBeenCalledTimes(1);
    expect(mockOnValidate).toHaveBeenCalledTimes(1);
    expect(mockOnValidate).toHaveBeenCalledWith('20');
  });

  test('displays error message', () => {
    render(
      <NumericInput
        id={testId} // Pass id
        label="Test Label"
        value="10"
        onChange={() => {}}
        error="Invalid input"
      />
    );
    expect(screen.getByText('Invalid input')).toBeInTheDocument();
    expect(screen.getByText('Invalid input')).toHaveStyle('color: red');
  });

  test('is disabled when disabled prop is true', () => {
    render(
      <NumericInput
        id={testId} // Pass id
        label="Test Label"
        value="10"
        onChange={() => {}}
        disabled={true}
      />
    );
    expect(screen.getByLabelText(/Test Label/i)).toBeDisabled();
  });
});
