import { render, screen, fireEvent } from '@testing-library/react';
import Layout from '@/components/Layout';
import MedicalDisclaimer from '@/components/MedicalDisclaimer';

describe('Layout Component', () => {
  it('should render header with logo and navigation', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    expect(screen.getByText('Drug Discovery Platform')).toBeInTheDocument();
    expect(screen.getByText('Home')).toBeInTheDocument();
    expect(screen.getByText('About')).toBeInTheDocument();
    expect(screen.getByText('API Docs')).toBeInTheDocument();
  });

  it('should render children content', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    expect(screen.getByText('Test Content')).toBeInTheDocument();
  });

  it('should render footer with links', () => {
    render(
      <Layout>
        <div>Test Content</div>
      </Layout>
    );

    expect(screen.getByText(/AI-powered drug discovery platform/i)).toBeInTheDocument();
    expect(screen.getByText('Open Targets')).toBeInTheDocument();
    expect(screen.getByText('ChEMBL Database')).toBeInTheDocument();
    expect(screen.getByText('AlphaFold Database')).toBeInTheDocument();
  });
});

describe('MedicalDisclaimer Component', () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it('should display disclaimer when not dismissed', () => {
    render(<MedicalDisclaimer />);

    expect(screen.getByText(/Medical Disclaimer/i)).toBeInTheDocument();
    expect(screen.getByText(/Research Purposes Only/i)).toBeInTheDocument();
  });

  it('should hide disclaimer when dismiss button is clicked', () => {
    render(<MedicalDisclaimer />);

    const dismissButton = screen.getByLabelText('Dismiss disclaimer');
    fireEvent.click(dismissButton);

    expect(screen.queryByText(/Medical Disclaimer/i)).not.toBeInTheDocument();
  });

  it('should persist dismissal to localStorage', () => {
    render(<MedicalDisclaimer />);

    const dismissButton = screen.getByLabelText('Dismiss disclaimer');
    fireEvent.click(dismissButton);

    expect(localStorage.getItem('disclaimer-dismissed')).toBe('true');
  });

  it('should not display if previously dismissed', () => {
    localStorage.setItem('disclaimer-dismissed', 'true');
    render(<MedicalDisclaimer />);

    expect(screen.queryByText(/Medical Disclaimer/i)).not.toBeInTheDocument();
  });
});
