import React from 'react';

export default function ProvenanceChip({ prov }) {
  if (!prov) return null;

  const conf = (prov.confidence || '').toUpperCase();
  let confClass = 'manual';
  if (conf === 'HIGH') confClass = 'high';
  else if (conf === 'MEDIUM') confClass = 'medium';

  // Shorten source if long
  let srcDisplay = prov.source || 'Unknown';
  if (srcDisplay.includes('Screener')) srcDisplay = 'Screener.in';
  else if (srcDisplay.includes('Workbook')) srcDisplay = 'Workbook';
  else if (srcDisplay.toLowerCase().includes('.pdf')) {
    srcDisplay = srcDisplay.length > 18 ? srcDisplay.substring(0, 15) + '…' : srcDisplay;
  }

  return (
    <span
      className={`provenance-chip ${confClass}`}
      title={`Source: ${prov.source} | Period: ${prov.period || 'N/A'} | Basis: ${prov.basis || 'N/A'} | Page: ${prov.page || 'N/A'} | Confidence: ${prov.confidence || 'N/A'}`}
    >
      <span>{srcDisplay}</span>
      {prov.page && <span style={{ opacity: 0.85, fontWeight: 600 }}>• p.{prov.page}</span>}
      {prov.period && <span style={{ opacity: 0.7 }}>• {prov.period}</span>}
      {prov.basis && prov.basis !== 'NOT_APPLICABLE' && (
        <span style={{ opacity: 0.7 }}>• {prov.basis === 'CONSOLIDATED' ? 'Consol' : 'Std'}</span>
      )}
      <span style={{ fontWeight: 700, marginLeft: '2px' }}>[{conf}]</span>
    </span>
  );
}
