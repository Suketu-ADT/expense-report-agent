import { useState } from 'react';
import { Download, FileUp, Receipt } from 'lucide-react';
import Card from './ui/Card';
import Badge from './ui/Badge';
import { api } from '../services/api';
import { formatDate, formatMoney } from '../utils/format';

const money = (paise, currency = 'INR') => formatMoney(paise == null ? null : paise / 100, currency);
const errorText = (error) => error.response?.data?.detail || 'Request failed. Please retry.';
const receiptTypes = '.pdf,.txt,.png,.jpg,.jpeg';
const receiptExtension = /\.(pdf|txt|png|jpe?g)$/i;
const claimStatus = {
  eligible: ['Eligible', 'success'],
  accepted: ['Accepted', 'success'],
  held: ['On hold', 'warning'],
  rejected: ['Rejected', 'error'],
};

function Claim({ item, index, revision, runId, onChange, closed, batchRunning }) {
  const [draft, setDraft] = useState(item.source);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [editing, setEditing] = useState(false);

  async function save(action, text = '') {
    setBusy(true);
    setError('');
    try {
      const result = await api.editClaim(runId, index, { revision, action, text, note });
      onChange(result);
      setNote('');
      setEditing(false);
    } catch (e) { setError(errorText(e)); }
    finally { setBusy(false); }
  }

  async function loadFile(file) {
    if (!file) return;
    setBusy(true);
    setError('');
    try {
      if (file.size > 5 * 1024 * 1024) throw new Error('Receipt exceeds 5 MB');
      const result = await api.attachReceipt(runId, index, revision, file);
      onChange(result);
      setDraft(result.items[index].source);
      setEditing(false);
    } catch (e) { setError(e.response ? errorText(e) : e.message); }
    finally { setBusy(false); }
  }

  const [statusLabel, tone] = claimStatus[item.status] || [item.status, 'neutral'];
  const amounts = [
    ['Claimed', money(item.claimed, item.currency)],
    ['Receipt total', money(item.evidence?.amount)],
    ['Approved', money(item.approved)],
  ];

  return <article className={`policy-item policy-item-${tone}`}>
    <header className="policy-heading">
      <div>
        <h4>{item.merchant}</h4>
        <p className="claim-meta">{item.id} · {formatDate(item.date)} · {item.category}</p>
      </div>
      <Badge tone={tone} dot>{statusLabel}</Badge>
    </header>
    <dl className="claim-amounts">
      {amounts.map(([label, value]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}
    </dl>
    <p className="claim-reason">
      {item.status === 'held' && !item.source ? item.agent_review?.verification || item.reason : item.reason}
    </p>
    {item.source && <details className="receipt-record">
      <summary>Receipt and decision record</summary>
      <div className="receipt-record-body">
        {item.document && <a className="link-btn" href={api.originalReceipt(runId, index)}>
          <Download size={14} aria-hidden="true" /> Download original receipt
        </a>}
        <pre>{item.source}</pre>
        <p>Current reading · {item.evidence?.merchant} · {formatDate(item.evidence?.date)} · {money(item.evidence?.amount)}</p>
        {item.events.filter(event => event.note).map((event, i) => <div className="receipt-event" key={i}>
          <strong>{event.action}</strong> {event.note}{event.text && <pre>{event.text}</pre>}
        </div>)}
        {item.agent_review && <p>{item.agent_review.action} {item.agent_review.verification}</p>}
      </div>
    </details>}
    {!closed && <fieldset disabled={busy || batchRunning} className="policy-controls">
      {editing ? <>
        {!item.source && <label>Attach original receipt <input type="file" accept=".pdf,.txt,.png,.jpg,.jpeg" onChange={e => loadFile(e.target.files[0])}/></label>}
        <label>Receipt text <textarea rows={4} maxLength={12000} value={draft} placeholder={'Merchant: Campus Cafe\nDate: 2026-07-10\nTotal: INR 1200'} onChange={e => setDraft(e.target.value)}/></label>
      </> : null}
      {(editing || item.status === 'held') && <label>Reviewer note <input maxLength={300} value={note} onChange={e => setNote(e.target.value)} /></label>}
      <div className="policy-actions">
        {editing ? <>
          <button className="btn btn-primary" disabled={!draft.trim() || (item.source && !note.trim())} onClick={() => save(item.source ? 'correct' : 'attach', draft)}>Save and check receipt</button>
          <button className="btn btn-secondary" onClick={() => setEditing(false)}>Cancel</button>
        </> : <>
          <button className="btn btn-secondary" onClick={() => {setDraft(item.events.filter(e => e.text).at(-1)?.text || item.source); setEditing(true);}}>{item.source ? 'Correct receipt fields' : 'Add receipt'}</button>
          {item.status === 'held' && <>
            {item.eligible != null && <button className="btn btn-primary" disabled={!note.trim()} onClick={() => save('accept')}>Accept {money(item.eligible)}</button>}
            <button className="btn btn-danger-outline" disabled={!note.trim()} onClick={() => save('reject')}>Reject claim</button>
          </>}
        </>}
      </div>
    </fieldset>}
    {error && <p role="alert">{String(error)}</p>}
  </article>;
}

export default function PolicyReview({data, runId, onChange, closed}) {
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [fileInputVersion, setFileInputVersion] = useState(0);
  if (!data) return null;

  function selectFiles(event) {
    const selected = Array.from(event.target.files).filter(file => receiptExtension.test(file.name));
    if (!selected.length) {
      setError('No supported receipts found. Choose PDF, TXT, PNG or JPEG files.');
    } else if (selected.length > 500) {
      setError('Choose up to 500 receipts at a time.');
    } else if (selected.reduce((total, file) => total + file.size, 0) > 100 * 1024 * 1024) {
      setError('Choose receipts totaling 100 MB or less.');
    } else {
      setError('');
      setFiles(selected);
      return;
    }
    setFiles([]);
    setFileInputVersion(version => version + 1);
  }

  async function reviewBatch(demo) {
    setBusy(true);
    setError('');
    try {
      const result = await api.reviewReceiptBatch(runId, data.revision, demo ? [] : files, demo);
      onChange(result);
      if (!demo) {
        setFiles([]);
        setFileInputVersion(version => version + 1);
      }
    } catch (e) {
      setError(errorText(e));
    } finally {
      setBusy(false);
    }
  }

  const review = data.receipt_review;
  const resolvedCount = review?.claims.filter(decision => decision.outcome === 'resolved').length ?? 0;
  const claims = data.items.map((item, index) => ({ item, index }));
  claims.sort((a, b) => Number(b.item.status === 'held') - Number(a.item.status === 'held'));
  return <Card id="reimbursement" icon={Receipt} title="Reimbursement review"
    description={'Meal limit ' + money(data.meal_cap * 100) + ' per claim'}
    actions={<a href={api.policyPdf(runId)} className="btn btn-secondary"><Download size={16} aria-hidden="true" /> Download PDF</a>}>
    <dl className="policy-totals">
      {[['Claimed', data.claimed], ['Approved', data.approved], ['Difference', data.difference]].map(([label, value]) =>
        <div key={label}><dt>{label}</dt><dd>{money(value)}</dd></div>)}
    </dl>

    {((!closed && data.held > 0) || review) && <section className="receipt-agents" aria-labelledby="receipt-batch-title">
      <h4 id="receipt-batch-title">Receipt matching</h4>
      {!closed && data.held > 0 && <fieldset disabled={busy} className="receipt-batch-controls">
        <div className="receipt-file">
          <FileUp size={19} aria-hidden="true" />
          <span>
            <strong aria-live="polite">{files.length ? files.length + (files.length === 1 ? ' receipt selected' : ' receipts selected') : 'Upload receipts'}</strong>
            <small>PDF, TXT, PNG or JPEG. Up to 500 files, 5 MB each and 100 MB total.</small>
          </span>
        </div>
        <div className="policy-actions">
          <label className="btn btn-secondary receipt-picker">
            Choose files
            <input key={`files-${fileInputVersion}`} className="visually-hidden" type="file" multiple accept={receiptTypes}
              onChange={selectFiles} />
          </label>
          <label className="btn btn-secondary receipt-picker">
            Choose folder
            <input key={`folder-${fileInputVersion}`} className="visually-hidden" type="file" webkitdirectory=""
              onChange={selectFiles} />
          </label>
          <button className="btn btn-primary" disabled={!files.length} onClick={() => reviewBatch(false)}>Match uploaded receipts</button>
          {data.resolution_demo && !review && <button className="btn btn-secondary" onClick={() => reviewBatch(true)}>Match sample receipts</button>}
        </div>
      </fieldset>}
      {busy && <p role="status">{files.length ? `Checking ${files.length} receipts for matches…` : 'Checking sample receipts…'}</p>}
      {error && <p className="text-error" role="alert">{String(error)}</p>}
      {review && <details className="receipt-results">
        <summary className="receipt-results-title">Last receipt batch · {resolvedCount} resolved, {review.claims.length - resolvedCount} sent to reviewer
          {review.files.length > 0 && `, ${review.files.length} file notices`}
        </summary>
        <ul className="receipt-agent-results">
          {review.claims.map(decision => <li key={decision.index}>
            <div className="receipt-result-header">
              <strong>{decision.claim_id}</strong>
              <Badge tone={decision.outcome === 'resolved' ? 'success' : 'warning'}>
                {decision.outcome === 'resolved' ? 'Resolved' : 'Sent to reviewer'}
              </Badge>
            </div>
            <span><b>Resolution agent</b> {decision.action}</span>
            <span><b>Evidence reviewer</b> {decision.verification}</span>
            {decision.debate && <details className="receipt-debate">
              <summary>AI debate between the two matching receipts (advisory only &mdash; this never decided the claim)</summary>
              {decision.debate.transcript.map((turn, i) => <p key={i}><b>{turn.role}</b> {turn.argument}</p>)}
              <p><b>Judge's pick</b> {decision.debate.opinion || 'No confident winner'}</p>
            </details>}
          </li>)}
          {review.files.map((file, index) => <li key={index}><strong>{file.name}</strong><span>{file.message}</span></li>)}
        </ul>
      </details>}
    </section>}

    <div className="claim-list-header">
      <h4>Claims</h4>
      <span role="status"><Badge tone={data.held ? 'warning' : 'success'} dot>
        {data.held ? data.held + ' on hold' : 'All decisions complete'}
      </Badge></span>
    </div>
    <div className="claim-list">
      {claims.map(({ item, index }) => <Claim key={index + ':' + Boolean(item.source)}
        {...{item,index,runId,onChange,closed}} revision={data.revision} batchRunning={busy}/>)}
    </div>
  </Card>;
}
