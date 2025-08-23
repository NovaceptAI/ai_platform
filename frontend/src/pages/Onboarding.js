import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import config from '../config';
import './Onboarding.css';

const AccountTypeCard = ({ type, label, disabled, selected, onSelect, note }) => (
  <button
    className={`type-card ${selected ? 'selected' : ''}`}
    disabled={disabled}
    onClick={() => onSelect(type)}
  >
    <div className="type-title">{label}</div>
    {note && <div className="type-note">{note}</div>}
  </button>
);

function ChipsInput({ label, value, onChange, placeholder }) {
  const [input, setInput] = useState('');
  const add = () => {
    const v = input.trim();
    if (!v) return;
    if (value.length >= 20) return;
    if (v.length > 60) return;
    onChange([...value, v]);
    setInput('');
  };
  return (
    <div className="field">
      <label>{label}</label>
      <div className="chips">
        {value.map((v, i) => (
          <span className="chip" key={i} onClick={() => onChange(value.filter((_, idx) => idx !== i))}>{v}</span>
        ))}
      </div>
      <div className="row">
        <input value={input} onChange={e => setInput(e.target.value)} placeholder={placeholder} />
        <button type="button" onClick={add}>Add</button>
      </div>
    </div>
  );
}

function LearnerForm({ data, setData }) {
  return (
    <>
      <div className="field"><label>School</label><input value={data.school} onChange={e=>setData({...data, school:e.target.value})} /></div>
      <div className="field"><label>Class</label><input value={data.class_name} onChange={e=>setData({...data, class_name:e.target.value})} /></div>
      <ChipsInput label="Favorite Subjects" value={data.favorite_subjects} onChange={v=>setData({...data, favorite_subjects:v})} placeholder="Add subject" />
      <ChipsInput label="Hobbies" value={data.hobbies} onChange={v=>setData({...data, hobbies:v})} placeholder="Add hobby" />
      <ChipsInput label="Interests" value={data.interests} onChange={v=>setData({...data, interests:v})} placeholder="Add interest" />
    </>
  );
}

function EducatorForm({ data, setData }) {
  return (
    <>
      <div className="field"><label>School</label><input value={data.school} onChange={e=>setData({...data, school:e.target.value})} /></div>
      <ChipsInput label="Subjects" value={data.subjects} onChange={v=>setData({...data, subjects:v})} placeholder="Add subject" />
      <ChipsInput label="Classes Taught" value={data.classes_taught} onChange={v=>setData({...data, classes_taught:v})} placeholder="Add class" />
      <div className="field"><label>Students Count</label><input type="number" value={data.students_count} onChange={e=>setData({...data, students_count:parseInt(e.target.value||'0',10)})} /></div>
      <div className="field"><label>Years Experience</label><input type="number" value={data.years_experience} onChange={e=>setData({...data, years_experience:parseInt(e.target.value||'0',10)})} /></div>
      <ChipsInput label="Hobbies" value={data.hobbies} onChange={v=>setData({...data, hobbies:v})} placeholder="Add hobby" />
    </>
  );
}

function ProfessionalForm({ data, setData }) {
  return (
    <>
      <div className="field"><label>Sector</label><input value={data.sector} onChange={e=>setData({...data, sector:e.target.value})} /></div>
      <div className="field"><label>Job Title</label><input value={data.job_title} onChange={e=>setData({...data, job_title:e.target.value})} /></div>
      <div className="field"><label>Designation</label><input value={data.designation} onChange={e=>setData({...data, designation:e.target.value})} /></div>
      <div className="field"><label>Years Experience</label><input type="number" value={data.years_experience} onChange={e=>setData({...data, years_experience:parseInt(e.target.value||'0',10)})} /></div>
      <ChipsInput label="Skills" value={data.skills} onChange={v=>setData({...data, skills:v})} placeholder="Add skill" />
      <ChipsInput label="Interests" value={data.interests} onChange={v=>setData({...data, interests:v})} placeholder="Add interest" />
      <ChipsInput label="Hobbies" value={data.hobbies} onChange={v=>setData({...data, hobbies:v})} placeholder="Add hobby" />
    </>
  );
}

function OrganizationForm({ data, setData }) {
  return (
    <>
      <div className="field"><label>Org Name</label><input value={data.org_name} onChange={e=>setData({...data, org_name:e.target.value})} /></div>
      <div className="field"><label>Contact Email</label><input value={data.contact_email} onChange={e=>setData({...data, contact_email:e.target.value})} /></div>
      <div className="field"><label>Website</label><input value={data.website} onChange={e=>setData({...data, website:e.target.value})} /></div>
    </>
  );
}

export default function Onboarding() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [step, setStep] = useState(1);
  const [type, setType] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Profile data per type
  const [learner, setLearner] = useState({ school:'', class_name:'', favorite_subjects:[], hobbies:[], interests:[] });
  const [educator, setEducator] = useState({ school:'', subjects:[], classes_taught:[], students_count:0, years_experience:0, hobbies:[] });
  const [professional, setProfessional] = useState({ sector:'', job_title:'', designation:'', years_experience:0, skills:[], interests:[], hobbies:[] });
  const [organization, setOrganization] = useState({ org_name:'', contact_email:'', website:'' });

const [token, setToken] = useState(localStorage.getItem('token') || '');
  // Handle token from oauth callback
// capture ?token= before making any API calls
useEffect(() => {
  const t = searchParams.get('token');
  if (t) {
    localStorage.setItem('token', t);
    setToken(t);
    // optional: remove token from URL
    const url = new URL(window.location.href);
    url.searchParams.delete('token');
    window.history.replaceState({}, '', url.pathname + url.search);
  }
}, [searchParams]);


  const begin = async (account_type) => {
  if (!token) { setError('Missing auth token. Please log in again.'); return; }
  setError('');
  setLoading(true);
  try {
    const resp = await fetch(`${config.API_BASE_URL}/onboarding/begin`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify({ account_type })
    });
      if (resp.status === 402) {
        const d = await resp.json();
        if (d.code === 'ORG_SUBSCRIPTION_REQUIRED') {
          setError('Organization requires paid subscription.');
          return;
        }
      }
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({}));
        throw new Error(d.error || 'Failed to begin onboarding');
      }
      setType(account_type);
      setStep(2);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const submitProfile = async () => {
    setError('');
    setLoading(true);
    try {
      const payload = type === 'learner' ? learner : type === 'educator' ? educator : type === 'professional' ? professional : organization;
      const resp = await fetch(`${config.API_BASE_URL}/onboarding/profile`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload)
      });
      if (!resp.ok) {
        const d = await resp.json().catch(() => ({}));
        throw new Error(d.error || 'Failed to submit profile');
      }
      setStep(3);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const finish = () => {
    navigate('/dashboard');
  };

  return (
    <div className="onboarding">
      <h1>Onboarding</h1>

      {error && <div className="error">{error}</div>}

      {step === 1 && (
        <div className="step-card">
          <h2>Choose Account Type</h2>
          <div className="type-grid">
            <AccountTypeCard type="learner" label="Learner" selected={type==='learner'} onSelect={begin} />
            <AccountTypeCard type="educator" label="Educator" selected={type==='educator'} onSelect={begin} />
            <AccountTypeCard type="professional" label="Professional" selected={type==='professional'} onSelect={begin} />
            <AccountTypeCard type="organization" label="Organization" selected={type==='organization'} onSelect={() => {}} disabled note="Requires paid subscription" />
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="step-card">
          <h2>Profile Details</h2>
          {type === 'learner' && <LearnerForm data={learner} setData={setLearner} />}
          {type === 'educator' && <EducatorForm data={educator} setData={setEducator} />}
          {type === 'professional' && <ProfessionalForm data={professional} setData={setProfessional} />}
          {type === 'organization' && <OrganizationForm data={organization} setData={setOrganization} />}
          <div className="actions">
            <button onClick={() => setStep(1)}>Back</button>
            <button onClick={submitProfile} disabled={loading}>Submit</button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="step-card">
          <h2>Onboarding Complete</h2>
          <p>You are all set.</p>
          <div className="actions">
            <button onClick={finish}>Go to Dashboard</button>
          </div>
        </div>
      )}
    </div>
  );
}

