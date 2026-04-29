import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@radix-ui/react-tabs';
import { PenLine, Database, Settings, Star, Trash2, Download, RefreshCw, Loader2, ThumbsUp, ThumbsDown, MessageSquare, LogOut } from 'lucide-react';
import * as api from './api';

function LoginPage({ onLogin }: { onLogin: () => void }) {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await api.login(username, password);
      onLogin();
    } catch {
      setError('Identifiants incorrects');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-8 w-full max-w-sm space-y-6">
        <div className="text-center">
          <PenLine className="w-10 h-10 text-indigo-600 mx-auto mb-3" />
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white">Writing Assistant</h1>
          <p className="text-slate-500 text-sm mt-1">Connectez-vous pour continuer</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Utilisateur</label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Mot de passe</label>
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
              required
            />
          </div>
          {error && <p className="text-red-500 text-sm text-center">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            Se connecter
          </button>
        </form>
      </div>
    </div>
  );
}

function App() {
  const [authenticated, setAuthenticated] = useState(api.isAuthenticated());
  const [stats, setStats] = useState<api.Stats | null>(null);
  const [styles, setStyles] = useState<api.Style[]>([]);

  useEffect(() => {
    if (!authenticated) return;
    api.getStats().then(setStats).catch(console.error);
    api.getStyles().then(setStyles).catch(console.error);
  }, [authenticated]);

  if (!authenticated) {
    return <LoginPage onLogin={() => setAuthenticated(true)} />;
  }

  const refreshStats = () => api.getStats().then(setStats);

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800">
      <header className="border-b border-slate-200 dark:border-slate-700 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-800 dark:text-white flex items-center gap-2">
            <PenLine className="w-6 h-6 text-indigo-600" />
            Writing Assistant
          </h1>
          <div className="flex items-center gap-4">
            {stats && (
              <div className="flex gap-4 text-sm text-slate-600 dark:text-slate-400">
                <span>{stats.total_examples} exemples</span>
                <span>{stats.golden_examples} golden</span>
                <span>Note moy: {(stats.average_rating ?? 0).toFixed(1)}</span>
              </div>
            )}
            <button
              onClick={api.logout}
              className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors"
              title="Se déconnecter"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6">
        <Tabs defaultValue="generate" className="space-y-6">
          <TabsList className="flex gap-2 bg-slate-100 dark:bg-slate-800 p-1 rounded-lg w-fit">
            <TabsTrigger value="generate" className="px-4 py-2 rounded-md data-[state=active]:bg-white dark:data-[state=active]:bg-slate-700 data-[state=active]:shadow-sm transition-all flex items-center gap-2">
              <PenLine className="w-4 h-4" /> Génération
            </TabsTrigger>
            <TabsTrigger value="curation" className="px-4 py-2 rounded-md data-[state=active]:bg-white dark:data-[state=active]:bg-slate-700 data-[state=active]:shadow-sm transition-all flex items-center gap-2">
              <Database className="w-4 h-4" /> Curation
            </TabsTrigger>
            <TabsTrigger value="config" className="px-4 py-2 rounded-md data-[state=active]:bg-white dark:data-[state=active]:bg-slate-700 data-[state=active]:shadow-sm transition-all flex items-center gap-2">
              <Settings className="w-4 h-4" /> Import & Config
            </TabsTrigger>
          </TabsList>

          <TabsContent value="generate">
            <GenerationTab styles={styles} onGenerate={refreshStats} />
          </TabsContent>

          <TabsContent value="curation">
            <CurationTab styles={styles} onUpdate={refreshStats} />
          </TabsContent>

          <TabsContent value="config">
            <ConfigTab onImport={refreshStats} />
          </TabsContent>
        </Tabs>
      </main>
    </div>
  );
}

function GenerationTab({ styles, onGenerate }: { styles: api.Style[]; onGenerate: () => void }) {
  const [prompt, setPrompt] = useState('');
  const [style, setStyle] = useState('email_decontracte');
  const [result, setResult] = useState<api.GenerateResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [rating, setRating] = useState<'up' | 'down' | null>(null);
  const [feedback, setFeedback] = useState('');
  const [showFeedback, setShowFeedback] = useState(false);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setResult(null);
    setRating(null);
    setFeedback('');
    setShowFeedback(false);
    try {
      const res = await api.generate({ prompt, style });
      setResult(res);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleRate = async (r: 'up' | 'down') => {
    if (!result) return;
    setRating(r);
    const ratingValue = r === 'up' ? 5 : 1;
    await api.rateGeneration(result.generation_id, ratingValue, feedback || undefined);
    onGenerate();
  };

  const handleSendFeedback = async () => {
    if (!result || !feedback.trim()) return;
    await api.rateGeneration(result.generation_id, rating === 'up' ? 5 : rating === 'down' ? 1 : 3, feedback);
    setShowFeedback(false);
    onGenerate();
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Nouvelle génération</h2>
        
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Prompt</label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Décrivez ce que vous voulez écrire..."
              className="w-full h-32 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 focus:ring-2 focus:ring-indigo-500 focus:border-transparent resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-600 dark:text-slate-400 mb-1">Style</label>
            <select
              value={style}
              onChange={(e) => setStyle(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700"
            >
              {styles.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
          </div>

          <button
            onClick={handleGenerate}
            disabled={loading || !prompt.trim()}
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white font-medium rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <PenLine className="w-4 h-4" />}
            {loading ? 'Génération...' : 'Générer'}
          </button>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Résultat</h2>
        
        {result ? (
          <>
            <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4 min-h-[200px] whitespace-pre-wrap text-slate-700 dark:text-slate-200">
              {result.text}
            </div>
            <div className="text-sm text-slate-500">
              {result.examples_used} exemples utilisés • {result.style}
            </div>
            
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                <span className="text-sm text-slate-600 dark:text-slate-400">Évaluer:</span>
                <button
                  onClick={() => handleRate('up')}
                  className={`p-2 rounded-lg transition-colors ${rating === 'up' ? 'bg-green-100 text-green-600' : 'text-slate-400 hover:bg-green-50 hover:text-green-500'}`}
                  title="Bon résultat"
                >
                  <ThumbsUp className="w-5 h-5" fill={rating === 'up' ? 'currentColor' : 'none'} />
                </button>
                <button
                  onClick={() => handleRate('down')}
                  className={`p-2 rounded-lg transition-colors ${rating === 'down' ? 'bg-red-100 text-red-600' : 'text-slate-400 hover:bg-red-50 hover:text-red-500'}`}
                  title="Mauvais résultat"
                >
                  <ThumbsDown className="w-5 h-5" fill={rating === 'down' ? 'currentColor' : 'none'} />
                </button>
                <button
                  onClick={() => setShowFeedback(!showFeedback)}
                  className={`p-2 rounded-lg transition-colors ${showFeedback ? 'bg-indigo-100 text-indigo-600' : 'text-slate-400 hover:bg-indigo-50 hover:text-indigo-500'}`}
                  title="Ajouter des instructions"
                >
                  <MessageSquare className="w-5 h-5" />
                </button>
                {rating && <span className="text-sm text-green-600 ml-2">✓ Évalué</span>}
              </div>
              
              {showFeedback && (
                <div className="space-y-2">
                  <textarea
                    value={feedback}
                    onChange={(e) => setFeedback(e.target.value)}
                    placeholder="Instructions de modification (ex: plus court, plus formel, ajouter une formule de politesse...)"
                    className="w-full h-20 px-3 py-2 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-sm resize-none"
                  />
                  <button
                    onClick={handleSendFeedback}
                    disabled={!feedback.trim()}
                    className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-400 text-white text-sm rounded-lg"
                  >
                    Envoyer le feedback
                  </button>
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4 min-h-[200px] flex items-center justify-center text-slate-400">
            Le résultat apparaîtra ici
          </div>
        )}
      </div>
    </div>
  );
}

function CurationTab({ styles, onUpdate }: { styles: api.Style[]; onUpdate: () => void }) {
  const [examples, setExamples] = useState<api.Example[]>([]);
  const [filterStyle, setFilterStyle] = useState('');
  const [goldenOnly, setGoldenOnly] = useState(false);
  const [loading, setLoading] = useState(false);

  const loadExamples = async () => {
    setLoading(true);
    try {
      const data = await api.getExamples({ 
        style: filterStyle || undefined, 
        golden_only: goldenOnly,
        limit: 50 
      });
      setExamples(data);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadExamples(); }, [filterStyle, goldenOnly]);

  const handleToggleGolden = async (id: string, current: boolean) => {
    await api.toggleGolden(id, !current);
    loadExamples();
    onUpdate();
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Supprimer cet exemple ?')) return;
    await api.deleteExample(id);
    loadExamples();
    onUpdate();
  };

  const handleExport = async () => {
    const res = await api.exportForFinetune();
    alert(`Exporté ${res.count} exemples vers ${res.path}`);
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-800 dark:text-white">Exemples ({examples.length})</h2>
          <div className="flex gap-3">
            <select
              value={filterStyle}
              onChange={(e) => setFilterStyle(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-600 bg-slate-50 dark:bg-slate-700 text-sm"
            >
              <option value="">Tous les styles</option>
              {styles.map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={goldenOnly}
                onChange={(e) => setGoldenOnly(e.target.checked)}
                className="rounded"
              />
              Golden uniquement
            </label>
            <button onClick={loadExamples} className="p-2 text-slate-500 hover:text-slate-700">
              <RefreshCw className="w-4 h-4" />
            </button>
          </div>
        </div>

        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
          </div>
        ) : (
          <div className="space-y-3 max-h-[500px] overflow-y-auto">
            {examples.map((ex) => (
              <div key={ex.id} className="bg-slate-50 dark:bg-slate-700 rounded-lg p-4 relative group">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    {ex.context && (
                      <div className="text-xs text-slate-500 mb-1 truncate">{ex.context}</div>
                    )}
                    <p className="text-sm text-slate-700 dark:text-slate-200 line-clamp-3">{ex.response}</p>
                    <div className="text-xs text-slate-400 mt-2">
                      {ex.style}
                    </div>
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleToggleGolden(ex.id, ex.is_golden)}
                      className={`p-1.5 rounded ${ex.is_golden ? 'text-yellow-500' : 'text-slate-400 hover:text-yellow-500'}`}
                      title={ex.is_golden ? 'Retirer golden' : 'Marquer golden'}
                    >
                      <Star className="w-4 h-4" fill={ex.is_golden ? 'currentColor' : 'none'} />
                    </button>
                    <button
                      onClick={() => handleDelete(ex.id)}
                      className="p-1.5 rounded text-slate-400 hover:text-red-500"
                      title="Supprimer"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">Réentraînement</h2>
        <div className="flex gap-4">
          <button
            onClick={handleExport}
            className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg flex items-center gap-2"
          >
            <Download className="w-4 h-4" /> Exporter pour fine-tuning
          </button>
          <button
            onClick={() => alert('Phase 2 - LoRA training à implémenter')}
            className="px-4 py-2 bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300 rounded-lg flex items-center gap-2"
          >
            <RefreshCw className="w-4 h-4" /> Lancer LoRA (Phase 2)
          </button>
        </div>
      </div>
    </div>
  );
}

function ConfigTab({ onImport }: { onImport: () => void }) {
  const [config, setConfig] = useState<api.Config | null>(null);
  const [importing, setImporting] = useState<string | null>(null);

  useEffect(() => {
    api.getConfig().then(setConfig).catch(console.error);
  }, []);

  const handleImport = async (source: 'slack' | 'whatsapp' | 'email') => {
    setImporting(source);
    try {
      const res = await api.importData(source);
      alert(res.message);
      onImport();
    } catch (e: any) {
      alert(`Erreur: ${e.response?.data?.detail || e.message}`);
    } finally {
      setImporting(null);
    }
  };

  const handleClear = async () => {
    if (!confirm('Supprimer TOUTES les données ? Cette action est irréversible.')) return;
    await api.clearDatabase();
    alert('Base vidée');
    onImport();
  };

  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">Configuration</h2>
        {config ? (
          <div className="space-y-3 text-sm">
            <div><span className="text-slate-500">Nom:</span> {config.your_name}</div>
            <div><span className="text-slate-500">Emails:</span> {config.your_emails.join(', ')}</div>
            <div><span className="text-slate-500">Slack:</span> {config.slack_folder || 'Non configuré'}</div>
            <div><span className="text-slate-500">WhatsApp:</span> {config.whatsapp_folder || 'Non configuré'}</div>
            <div><span className="text-slate-500">Email:</span> {config.email_folder || 'Non configuré'}</div>
            <p className="text-xs text-slate-400 mt-4">Modifier my_config.yaml pour changer ces paramètres</p>
          </div>
        ) : (
          <p className="text-slate-500">Chargement...</p>
        )}
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-slate-800 dark:text-white mb-4">Import de données</h2>
        <div className="grid grid-cols-3 gap-4">
          {(['email', 'slack', 'whatsapp'] as const).map((source) => (
            <button
              key={source}
              onClick={() => handleImport(source)}
              disabled={importing !== null}
              className="px-4 py-3 bg-indigo-50 dark:bg-indigo-900/30 hover:bg-indigo-100 dark:hover:bg-indigo-900/50 text-indigo-700 dark:text-indigo-300 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
            >
              {importing === source ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
              Importer {source}
            </button>
          ))}
        </div>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-sm p-6">
        <h2 className="text-lg font-semibold text-red-600 mb-4">Zone dangereuse</h2>
        <button
          onClick={handleClear}
          className="px-4 py-2 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg"
        >
          Vider la base de données
        </button>
      </div>
    </div>
  );
}

export default App;
