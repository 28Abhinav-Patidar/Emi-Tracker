
import { useEffect, useState } from "react";
import "./App.css";


const emptyForm = {
  applicant_name: "",
  applicant_email: "",
  principal: "100000",
  annual_interest_rate: "12",
  tenure_months: "12",
};

const money = (value) =>
  new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
    minimumFractionDigits: 2,
  }).format(Number(value));

function App() {
  const [form, setForm] = useState(emptyForm);
  const [loans, setLoans] = useState([]);
  const [selectedLoan, setSelectedLoan] = useState(null);
  const [schedule, setSchedule] = useState([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function api(path, options = {}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...options.headers,
      },
    });

    const data = await response.json().catch(() => ({}));

    if (!response.ok) {
      const detail = data.detail || data.error ||
        Object.entries(data)
          .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(", ") : value}`)
          .join(" | ");

      throw new Error(detail || `Request failed (${response.status})`);
    }

    return data;
  }

  
async function loadLoans() {
  try {
    const data = await api("/api/loans/");

    console.log("Loans API response:", data);

    // Django REST Framework may return a paginated response.
    if (Array.isArray(data)) {
      setLoans(data);
    } else if (Array.isArray(data.results)) {
      setLoans(data.results);
    } else {
      console.error("Unexpected loans API response:", data);
      setLoans([]);
      setError("Unexpected response from the loans API.");
    }
  } catch (err) {
    setError(`Could not load loans: ${err.message}`);
  }
}


  useEffect(() => {
    loadLoans();
  }, []);

  const principal = Number(form.principal);
  const annualRate = Number(form.annual_interest_rate);
  const months = Number(form.tenure_months);
  const monthlyRate = annualRate / 1200;
  const calculatedEmi =
    principal > 0 && months > 0
      ? monthlyRate === 0
        ? principal / months
        : (principal * monthlyRate * Math.pow(1 + monthlyRate, months)) /
          (Math.pow(1 + monthlyRate, months) - 1)
      : 0;

  function updateField(event) {
    setForm({ ...form, [event.target.name]: event.target.value });
  }

  async function submitLoan(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const loan = await api("/api/loans/", {
        method: "POST",
        body: JSON.stringify({
          ...form,
          principal: Number(form.principal).toFixed(2),
          annual_interest_rate: Number(form.annual_interest_rate).toFixed(2),
          tenure_months: Number(form.tenure_months),
        }),
      });

      setMessage(`Application submitted successfully. Loan ID: ${loan.id}`);
      setForm(emptyForm);
      await loadLoans();
      await openLoan(loan.id);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  async function openLoan(id) {
    setError("");
    setMessage("");

    try {
      const [loan, rows] = await Promise.all([
        api(`/api/loans/${id}/`),
        api(`/api/loans/${id}/schedule/`),
      ]);
      setSelectedLoan(loan);
      setSchedule(rows);
    } catch (err) {
      setError(err.message);
    }
  }

  async function changeStatus(id, status) {
    setError("");
    setMessage("");

    try {
      await api(`/api/loans/${id}/status/`, {
        method: "PATCH",
        body: JSON.stringify({ status }),
      });
      setMessage(`Loan ${id} marked ${status.toLowerCase()}.`);
      await loadLoans();
      await openLoan(id);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <main className="app-shell">

      {error && <div className="notice error" role="alert">{error}</div>}
      {message && <div className="notice success" role="status">{message}</div>}

      <section className="stats-grid">
        <article className="stat-card">
          <span>Total applications</span>
          <strong>{loans.length}</strong>
        </article>
        <article className="stat-card">
          <span>Pending applications</span>
          <strong>{loans.filter((loan) => loan.status === "PENDING").length}</strong>
        </article>
        <article className="stat-card">
          <span>Approved applications</span>
          <strong>{loans.filter((loan) => loan.status === "APPROVED").length}</strong>
        </article>
      </section>

      <section className="main-grid">
        <article className="panel">
          <div className="panel-heading">
            <div>
              <h3>Apply for a loan</h3>
            </div>
          </div>

          <form onSubmit={submitLoan} className="loan-form">
            <label>
              Applicant name
              <input
                name="applicant_name"
                value={form.applicant_name}
                onChange={updateField}
                placeholder="Enter full name"
                maxLength={150}
                required
              />
            </label>

            <label>
              Email address
              <input
                type="email"
                name="applicant_email"
                value={form.applicant_email}
                onChange={updateField}
                placeholder="you@example.com"
                required
              />
            </label>
              <label>
                Loan amount (₹)
                <input
                  type="number"
                  name="principal"
                  value={form.principal}
                  onChange={updateField}
                  min="10000"
                  max="5000000"
                  step="0.01"
                  required
                />
                <small>₹10,000 – ₹50,00,000</small>
              </label>

            <label>
                Annual interest (%)
                <input
                  type="number"
                  name="annual_interest_rate"
                  value={form.annual_interest_rate}
                  onChange={updateField}
                  min="1"
                  max="36"
                  step="0.5"
                  required
                />
                <small>1% – 36%</small>
              </label>

            <label>
              Tenure
              <select
                name="tenure_months"
                value={form.tenure_months}
                onChange={updateField}
                required
              >
                {[3, 6, 9, 12, 18, 24, 36, 48, 60].map((month) => (
                  <option key={month} value={month}>{month} months</option>
                ))}
              </select>
            </label>

            <div className="emi-preview">
              <span>Your Estimated monthly EMI</span>
              <strong>{money(calculatedEmi || 0)}</strong>
            </div>

            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Submitting..." : "Submit application →"}
            </button>
          </form>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <h3>Recent applications</h3>
            </div>
          </div>

          <div className="loan-list">
            {loans.length === 0 ? (
              <div className="empty-state">
                <span>▤</span>
                <strong>No applications yet</strong>
                <p>Your submitted loan applications will appear here.</p>
              </div>
            ) : (
              loans.map((loan) => (
                <div
                  className={`loan-item ${selectedLoan?.id === loan.id ? "selected" : ""}`}
                  key={loan.id}
                >
                  <button
                    className="loan-summary"
                    type="button"
                    onClick={() => openLoan(loan.id)}
                  >
                   
                    <span className="loan-person">
                      <strong>{loan.applicant_name}</strong>
                      <small>Loan #{loan.id} · {loan.tenure_months} months</small>
                    </span>
                    <span className={`status status-${loan.status.toLowerCase()}`}>
                      {loan.status}
                    </span>
                  </button>
                  <div className="loan-meta">
                    <strong>{money(loan.principal)}</strong>
                    <span>EMI {money(loan.emi)}</span>
                  </div>
                  {loan.status === "PENDING" && (
                    <div className="decision-actions">
                      <button
                        type="button"
                        className="approve-button"
                        onClick={() => changeStatus(loan.id, "APPROVED")}
                      >
                        Approve
                      </button>
                      <button
                        type="button"
                        className="reject-button"
                        onClick={() => changeStatus(loan.id, "REJECTED")}
                      >
                        Reject
                      </button>
                    </div>
                  )}
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      {selectedLoan && (
        <section className="panel schedule-panel">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">LOAN #{selectedLoan.id}</p>
              <h3>Repayment schedule</h3>
              <p className="muted">
                {selectedLoan.applicant_name} · {selectedLoan.applicant_email}
              </p>
            </div>
            <button
              type="button"
              className="refresh-button"
              onClick={() => {
                setSelectedLoan(null);
                setSchedule([]);
              }}
            >
              Close
            </button>
          </div>

          <div className="schedule-summary">
            <div><span>Monthly EMI</span><strong>{money(selectedLoan.emi)}</strong></div>
            <div><span>Total interest</span><strong>{money(selectedLoan.total_interest)}</strong></div>
            <div><span>Total payable</span><strong>{money(selectedLoan.total_payable)}</strong></div>
          </div>

          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Month</th>
                  <th>EMI</th>
                  <th>Principal</th>
                  <th>Interest</th>
                  <th>Remaining balance</th>
                </tr>
              </thead>
              <tbody>
                {schedule.map((row) => (
                  <tr key={row.month}>
                    <td>{row.month}</td>
                    <td>{money(row.emi)}</td>
                    <td>{money(row.principal_component)}</td>
                    <td>{money(row.interest_component)}</td>
                    <td>{money(row.remaining_balance)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      <footer>VariCash · Loan EMI Tracker · Built with React, Django & PostgreSQL</footer>
    </main>
  );
}

export default App;
