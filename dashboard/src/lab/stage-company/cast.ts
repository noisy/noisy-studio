export interface CompanyPerson { id: string; name: string; role: string; voice: string; working?: boolean }
export interface CompanyDepartment { id: string; name: string; purpose: string; color: string; lead: CompanyPerson; workers: CompanyPerson[] }
export const departments: CompanyDepartment[] = [
  { id: 'development', name: 'Development', purpose: 'Make it work beautifully.', color: '#b5cafa', lead: { id: 'dev-lead', working: true, name: 'Orion', role: 'Engineering lead', voice: 'orion' }, workers: [
    { id: 'dev-1', working: true, name: 'Kepler', role: 'Architecture', voice: 'kepler' }, { id: 'dev-2', working: true, name: 'Helix', role: 'Interfaces', voice: 'helix' }, { id: 'dev-3', name: 'Cosmo', role: 'Infrastructure', voice: 'cosmo' }] },
  { id: 'design', name: 'Design studio', purpose: 'Give good ideas a face.', color: '#edb9d0', lead: { id: 'design-lead', working: true, name: 'Iris', role: 'Design lead', voice: 'iris' }, workers: [
    { id: 'design-1', working: true, name: 'Luna', role: 'Visual design', voice: 'luna' }, { id: 'design-2', name: 'Lumen', role: 'Motion', voice: 'lumen' }, { id: 'design-3', name: 'Aurora', role: 'Illustration', voice: 'aurora' }] },
  { id: 'marketing', name: 'Marketing', purpose: 'Find the story worth telling.', color: '#efc58f', lead: { id: 'marketing-lead', working: true, name: 'Lux', role: 'Marketing lead', voice: 'lux' }, workers: [
    { id: 'marketing-1', name: 'Ara', role: 'Editorial', voice: 'ara' }, { id: 'marketing-2', working: true, name: 'Celeste', role: 'Community', voice: 'celeste' }, { id: 'marketing-3', name: 'Leo', role: 'Research', voice: 'leo' }] },
  { id: 'quality', name: 'Quality lab', purpose: 'Ask the awkward questions.', color: '#b8dfad', lead: { id: 'quality-lead', name: 'Rex', role: 'Quality lead', voice: 'rex' }, workers: [
    { id: 'quality-1', working: true, name: 'Eve', role: 'Testing', voice: 'eve' }, { id: 'quality-2', name: 'Rigel', role: 'Accessibility', voice: 'rigel' }, { id: 'quality-3', name: 'Sal', role: 'Reliability', voice: 'sal' }] },
];
