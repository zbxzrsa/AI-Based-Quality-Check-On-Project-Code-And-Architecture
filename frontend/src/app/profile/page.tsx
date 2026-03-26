'use client';

import { useState, useEffect } from 'react';
import MainLayout from '@/components/layout/main-layout';
import { PageHeader } from '@/components/layout/page-header';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Avatar } from '@/components/ui/avatar';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useToast } from '@/hooks/use-toast';
import {
  Mail,
  Calendar,
  GitPullRequest,
  CheckCircle2,
  AlertCircle,
  Key,
  Eye,
  EyeOff,
  Save,
  Trash2,
  UserCircle2,
} from 'lucide-react';
import { apiClient } from '@/lib/api-client';

interface APISettings {
  openrouter_api_key_set: boolean;
  openai_api_key_set: boolean;
  anthropic_api_key_set: boolean;
  deepseek_api_key_set: boolean;
  google_api_key_set: boolean;
  chatglm_api_key_set: boolean;
  ollama_base_url: string | null;
  ollama_model: string | null;
  lmstudio_base_url: string | null;
  lmstudio_model: string | null;
  deepseek_base_url: string | null;
  deepseek_model: string | null;
  google_base_url: string | null;
  google_model: string | null;
  chatglm_base_url: string | null;
  chatglm_model: string | null;
  default_llm_provider: string | null;
  default_llm_model: string | null;
}

interface APISettingsUpdatePayload {
  default_llm_provider: string;
  default_llm_model: string;
  openrouter_api_key?: string;
  openai_api_key?: string;
  anthropic_api_key?: string;
  deepseek_api_key?: string;
  google_api_key?: string;
  chatglm_api_key?: string;
  ollama_base_url?: string;
  ollama_model?: string;
  lmstudio_base_url?: string;
  lmstudio_model?: string;
  deepseek_base_url?: string;
  deepseek_model?: string;
  google_base_url?: string;
  google_model?: string;
  chatglm_base_url?: string;
  chatglm_model?: string;
}

export default function ProfilePage() {
  const { toast } = useToast();
  const [isLoading, setIsLoading] = useState(false);
  const [showKeys, setShowKeys] = useState({
    openrouter: false,
    openai: false,
    anthropic: false,
    deepseek: false,
    google: false,
    chatglm: false,
  });

  // API Settings State
  const [apiSettings, setApiSettings] = useState<APISettings>({
    openrouter_api_key_set: false,
    openai_api_key_set: false,
    anthropic_api_key_set: false,
    deepseek_api_key_set: false,
    google_api_key_set: false,
    chatglm_api_key_set: false,
    ollama_base_url: null,
    ollama_model: null,
    lmstudio_base_url: null,
    lmstudio_model: null,
    deepseek_base_url: null,
    deepseek_model: null,
    google_base_url: null,
    google_model: null,
    chatglm_base_url: null,
    chatglm_model: null,
    default_llm_provider: null,
    default_llm_model: null,
  });

  const [apiKeys, setApiKeys] = useState({
    openrouter: '',
    openai: '',
    anthropic: '',
    deepseek: '',
    google: '',
    chatglm: '',
  });

  const [endpointSettings, setEndpointSettings] = useState({
    ollama_base_url: '',
    ollama_model: '',
    lmstudio_base_url: '',
    lmstudio_model: '',
    deepseek_base_url: '',
    deepseek_model: '',
    google_base_url: '',
    google_model: '',
    chatglm_base_url: '',
    chatglm_model: '',
  });

  const [defaultProvider, setDefaultProvider] = useState('openrouter');
  const [defaultModel, setDefaultModel] = useState('anthropic/claude-3.5-sonnet');

  const getApiErrorMessage = (error: unknown, fallback: string) => {
    if (typeof error === 'object' && error !== null && 'response' in error) {
      const response = (error as { response?: { data?: { detail?: string } } }).response;
      return response?.data?.detail || fallback;
    }

    return fallback;
  };

  const loadAPISettings = async () => {
    try {
      const settings = await apiClient.get<APISettings>('/user/settings/api-settings');
      setApiSettings(settings);
      if (settings.default_llm_provider) {
        setDefaultProvider(settings.default_llm_provider);
      }
      if (settings.default_llm_model) {
        setDefaultModel(settings.default_llm_model);
      }
      setEndpointSettings({
        ollama_base_url: settings.ollama_base_url || '',
        ollama_model: settings.ollama_model || '',
        lmstudio_base_url: settings.lmstudio_base_url || '',
        lmstudio_model: settings.lmstudio_model || '',
        deepseek_base_url: settings.deepseek_base_url || '',
        deepseek_model: settings.deepseek_model || '',
        google_base_url: settings.google_base_url || '',
        google_model: settings.google_model || '',
        chatglm_base_url: settings.chatglm_base_url || '',
        chatglm_model: settings.chatglm_model || '',
      });
    } catch {
      // API settings endpoint may not exist, ignore gracefully
    }
  };

  // Load API settings on mount
  useEffect(() => {
    loadAPISettings();
  }, []);

  const handleSaveAPISettings = async () => {
    setIsLoading(true);
    try {
      const updateData: APISettingsUpdatePayload = {
        default_llm_provider: defaultProvider,
        default_llm_model: defaultModel,
      };

      // Only include API keys that have been entered
      if (apiKeys.openrouter) {
        updateData.openrouter_api_key = apiKeys.openrouter;
      }
      if (apiKeys.openai) {
        updateData.openai_api_key = apiKeys.openai;
      }
      if (apiKeys.anthropic) {
        updateData.anthropic_api_key = apiKeys.anthropic;
      }
      if (apiKeys.deepseek) {
        updateData.deepseek_api_key = apiKeys.deepseek;
      }
      if (apiKeys.google) {
        updateData.google_api_key = apiKeys.google;
      }
      if (apiKeys.chatglm) {
        updateData.chatglm_api_key = apiKeys.chatglm;
      }

      updateData.ollama_base_url = endpointSettings.ollama_base_url;
      updateData.ollama_model = endpointSettings.ollama_model;
      updateData.lmstudio_base_url = endpointSettings.lmstudio_base_url;
      updateData.lmstudio_model = endpointSettings.lmstudio_model;
      updateData.deepseek_base_url = endpointSettings.deepseek_base_url;
      updateData.deepseek_model = endpointSettings.deepseek_model;
      updateData.google_base_url = endpointSettings.google_base_url;
      updateData.google_model = endpointSettings.google_model;
      updateData.chatglm_base_url = endpointSettings.chatglm_base_url;
      updateData.chatglm_model = endpointSettings.chatglm_model;

      await apiClient.put('/user/settings/api-settings', updateData);

      toast({
        title: 'Success',
        description: 'API settings saved successfully',
      });

      // Clear input fields and reload settings
      setApiKeys({
        openrouter: '',
        openai: '',
        anthropic: '',
        deepseek: '',
        google: '',
        chatglm: '',
      });
      await loadAPISettings();
    } catch (error: unknown) {
      toast({
        title: 'Error',
        description: getApiErrorMessage(error, 'Failed to save API settings'),
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleDeleteAPIKey = async (provider: string) => {
    if (!confirm(`Are you sure you want to delete your ${provider} API key?`)) {
      return;
    }

    setIsLoading(true);
    try {
      await apiClient.delete(`/user/settings/api-settings/${provider}`);

      toast({
        title: 'Success',
        description: `${provider} API key deleted successfully`,
      });

      await loadAPISettings();
    } catch (error: unknown) {
      toast({
        title: 'Error',
        description: getApiErrorMessage(error, 'Failed to delete API key'),
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
    }
  };

  // Mock user data
  const user = {
    name: 'John Doe',
    email: 'john.doe@example.com',
    role: 'Developer',
    joinedDate: '2026-01-01',
    avatar: null,
  };

  const stats = {
    totalReviews: 45,
    approvedPRs: 38,
    pendingReviews: 7,
    criticalIssuesFound: 12,
  };

  const recentActivity = [
    {
      id: '1',
      type: 'review',
      title: 'Reviewed PR #123',
      project: 'AI Code Review Platform',
      date: '2026-01-19',
      status: 'approved',
    },
    {
      id: '2',
      type: 'issue',
      title: 'Found critical security issue',
      project: 'E-commerce API',
      date: '2026-01-18',
      status: 'critical',
    },
    {
      id: '3',
      type: 'review',
      title: 'Reviewed PR #456',
      project: 'Analytics Dashboard',
      date: '2026-01-17',
      status: 'changes_requested',
    },
  ];

  return (
    <MainLayout>
      <div className="space-y-6">
        <PageHeader
          title="Profile"
          description="Manage your personal workspace, recent review activity, and AI provider configuration inside the unified dashboard shell."
        />

        {/* Profile Header */}
        <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
          <div className="flex items-center gap-6">
            <Avatar className="h-24 w-24">
              <div className="h-full w-full rounded-full bg-primary flex items-center justify-center text-primary-foreground text-3xl font-bold">
                {user.name
                  .split(' ')
                  .map((n) => n[0])
                  .join('')}
              </div>
            </Avatar>
            <div>
              <div className="flex items-center gap-2">
                <UserCircle2 className="h-5 w-5 text-sky-600 dark:text-sky-300" />
                <h2 className="text-3xl font-bold">{user.name}</h2>
              </div>
              <div className="flex items-center gap-4 mt-2 text-muted-foreground">
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4" />
                  <span>{user.email}</span>
                </div>
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4" />
                  <span>Joined {new Date(user.joinedDate).toLocaleDateString()}</span>
                </div>
              </div>
              <Badge className="mt-2">{user.role}</Badge>
            </div>
          </div>
        </Card>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Total Reviews</p>
                <p className="text-3xl font-bold mt-2">{stats.totalReviews}</p>
              </div>
              <GitPullRequest className="h-8 w-8 text-blue-500" />
            </div>
          </Card>

          <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Approved PRs</p>
                <p className="text-3xl font-bold mt-2">{stats.approvedPRs}</p>
              </div>
              <CheckCircle2 className="h-8 w-8 text-green-500" />
            </div>
          </Card>

          <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Pending Reviews</p>
                <p className="text-3xl font-bold mt-2">{stats.pendingReviews}</p>
              </div>
              <AlertCircle className="h-8 w-8 text-yellow-500" />
            </div>
          </Card>

          <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-muted-foreground">Critical Issues</p>
                <p className="text-3xl font-bold mt-2">{stats.criticalIssuesFound}</p>
              </div>
              <AlertCircle className="h-8 w-8 text-red-500" />
            </div>
          </Card>
        </div>

        {/* Activity Tabs */}
        <Tabs defaultValue="activity" className="w-full">
          <TabsList>
            <TabsTrigger value="activity">Recent Activity</TabsTrigger>
            <TabsTrigger value="api-settings">API Settings</TabsTrigger>
            <TabsTrigger value="projects">Projects</TabsTrigger>
            <TabsTrigger value="achievements">Achievements</TabsTrigger>
          </TabsList>

          <TabsContent value="activity" className="space-y-4">
            <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
              <h3 className="text-lg font-semibold mb-4">Recent Activity</h3>
              <div className="space-y-4">
                {recentActivity.map((activity) => (
                  <div
                    key={activity.id}
                    className="flex items-center justify-between p-4 rounded-lg border"
                  >
                    <div className="flex-1">
                      <h4 className="font-medium">{activity.title}</h4>
                      <p className="text-sm text-muted-foreground">
                        {activity.project}
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <span className="text-sm text-muted-foreground">
                        {new Date(activity.date).toLocaleDateString()}
                      </span>
                      <Badge
                        className={
                          activity.status === 'approved'
                            ? 'bg-green-500'
                            : activity.status === 'critical'
                              ? 'bg-red-500'
                              : 'bg-yellow-500'
                        }
                      >
                        {activity.status.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="api-settings" className="space-y-4">
            <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
              <div className="flex items-center gap-2 mb-6">
                <Key className="h-5 w-5" />
                <h3 className="text-lg font-semibold">API Configuration</h3>
              </div>

              <p className="text-sm text-muted-foreground mb-6">
                Configure your personal API keys for AI code review services. Your keys are encrypted and stored securely.
              </p>

              <div className="space-y-6">
                {/* Default Provider Selection */}
                <div className="space-y-2">
                  <Label>Default LLM Provider</Label>
                  <Select value={defaultProvider} onValueChange={setDefaultProvider}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openrouter">OpenRouter</SelectItem>
                      <SelectItem value="openai">OpenAI</SelectItem>
                      <SelectItem value="anthropic">Anthropic</SelectItem>
                      <SelectItem value="deepseek">DeepSeek</SelectItem>
                      <SelectItem value="google">Google Gemini</SelectItem>
                      <SelectItem value="chatglm">ChatGLM</SelectItem>
                      <SelectItem value="ollama">Ollama</SelectItem>
                      <SelectItem value="lmstudio">LM Studio</SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Choose which AI provider to use by default for code reviews
                  </p>
                </div>

                {/* Default Model Selection */}
                <div className="space-y-2">
                  <Label>Default Model</Label>
                  <Input
                    value={defaultModel}
                    onChange={(e) => setDefaultModel(e.target.value)}
                    placeholder="e.g., anthropic/claude-3.5-sonnet"
                  />
                  <p className="text-xs text-muted-foreground">
                    Specify the model to use (e.g., gpt-4, claude-3.5-sonnet)
                  </p>
                </div>

                <div className="border-t pt-6">
                  <h4 className="font-semibold mb-4">API Keys</h4>

                  {/* OpenRouter API Key */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between">
                      <Label>OpenRouter API Key</Label>
                      {apiSettings.openrouter_api_key_set && (
                        <Badge variant="success" className="text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Configured
                        </Badge>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          type={showKeys.openrouter ? 'text' : 'password'}
                          value={apiKeys.openrouter}
                          onChange={(e) => setApiKeys({ ...apiKeys, openrouter: e.target.value })}
                          placeholder="sk-or-v1-..."
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full"
                          onClick={() => setShowKeys({ ...showKeys, openrouter: !showKeys.openrouter })}
                        >
                          {showKeys.openrouter ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {apiSettings.openrouter_api_key_set && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteAPIKey('openrouter')}
                          disabled={isLoading}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Get your API key from{' '}
                      <a
                        href="https://openrouter.ai/keys"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        OpenRouter
                      </a>
                    </p>
                  </div>

                  {/* OpenAI API Key */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between">
                      <Label>OpenAI API Key</Label>
                      {apiSettings.openai_api_key_set && (
                        <Badge variant="success" className="text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Configured
                        </Badge>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          type={showKeys.openai ? 'text' : 'password'}
                          value={apiKeys.openai}
                          onChange={(e) => setApiKeys({ ...apiKeys, openai: e.target.value })}
                          placeholder="sk-..."
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full"
                          onClick={() => setShowKeys({ ...showKeys, openai: !showKeys.openai })}
                        >
                          {showKeys.openai ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {apiSettings.openai_api_key_set && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteAPIKey('openai')}
                          disabled={isLoading}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Get your API key from{' '}
                      <a
                        href="https://platform.openai.com/api-keys"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        OpenAI
                      </a>
                    </p>
                  </div>

                  {/* Anthropic API Key */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between">
                      <Label>Anthropic API Key</Label>
                      {apiSettings.anthropic_api_key_set && (
                        <Badge variant="success" className="text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Configured
                        </Badge>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          type={showKeys.anthropic ? 'text' : 'password'}
                          value={apiKeys.anthropic}
                          onChange={(e) => setApiKeys({ ...apiKeys, anthropic: e.target.value })}
                          placeholder="sk-ant-..."
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full"
                          onClick={() => setShowKeys({ ...showKeys, anthropic: !showKeys.anthropic })}
                        >
                          {showKeys.anthropic ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {apiSettings.anthropic_api_key_set && (
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDeleteAPIKey('anthropic')}
                          disabled={isLoading}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground">
                      Get your API key from{' '}
                      <a
                        href="https://console.anthropic.com/settings/keys"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        Anthropic
                      </a>
                    </p>
                  </div>

                  {/* DeepSeek API Key */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between">
                      <Label>DeepSeek API Key</Label>
                      {apiSettings.deepseek_api_key_set && (
                        <Badge variant="success" className="text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Configured
                        </Badge>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          type={showKeys.deepseek ? 'text' : 'password'}
                          value={apiKeys.deepseek}
                          onChange={(e) => setApiKeys({ ...apiKeys, deepseek: e.target.value })}
                          placeholder="sk-..."
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full"
                          onClick={() => setShowKeys({ ...showKeys, deepseek: !showKeys.deepseek })}
                        >
                          {showKeys.deepseek ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {apiSettings.deepseek_api_key_set && (
                        <Button variant="destructive" size="sm" onClick={() => handleDeleteAPIKey('deepseek')} disabled={isLoading}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Google API Key */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between">
                      <Label>Google Gemini API Key</Label>
                      {apiSettings.google_api_key_set && (
                        <Badge variant="success" className="text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Configured
                        </Badge>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          type={showKeys.google ? 'text' : 'password'}
                          value={apiKeys.google}
                          onChange={(e) => setApiKeys({ ...apiKeys, google: e.target.value })}
                          placeholder="AIza..."
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full"
                          onClick={() => setShowKeys({ ...showKeys, google: !showKeys.google })}
                        >
                          {showKeys.google ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {apiSettings.google_api_key_set && (
                        <Button variant="destructive" size="sm" onClick={() => handleDeleteAPIKey('google')} disabled={isLoading}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* ChatGLM API Key */}
                  <div className="space-y-2 mb-4">
                    <div className="flex items-center justify-between">
                      <Label>ChatGLM API Key</Label>
                      {apiSettings.chatglm_api_key_set && (
                        <Badge variant="success" className="text-xs">
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                          Configured
                        </Badge>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <div className="relative flex-1">
                        <Input
                          type={showKeys.chatglm ? 'text' : 'password'}
                          value={apiKeys.chatglm}
                          onChange={(e) => setApiKeys({ ...apiKeys, chatglm: e.target.value })}
                          placeholder="your-chatglm-key"
                        />
                        <Button
                          type="button"
                          variant="ghost"
                          size="sm"
                          className="absolute right-0 top-0 h-full"
                          onClick={() => setShowKeys({ ...showKeys, chatglm: !showKeys.chatglm })}
                        >
                          {showKeys.chatglm ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </Button>
                      </div>
                      {apiSettings.chatglm_api_key_set && (
                        <Button variant="destructive" size="sm" onClick={() => handleDeleteAPIKey('chatglm')} disabled={isLoading}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>

                  {/* Endpoint Settings */}
                  <div className="space-y-3 mb-4">
                    <Label>Local/Compatible Endpoint Settings</Label>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <Input
                        value={endpointSettings.ollama_base_url}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, ollama_base_url: e.target.value })}
                        placeholder="Ollama base URL (e.g. http://localhost:11434)"
                      />
                      <Input
                        value={endpointSettings.ollama_model}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, ollama_model: e.target.value })}
                        placeholder="Ollama model (e.g. llama3.1)"
                      />
                      <Input
                        value={endpointSettings.lmstudio_base_url}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, lmstudio_base_url: e.target.value })}
                        placeholder="LM Studio base URL (e.g. http://localhost:1234/v1)"
                      />
                      <Input
                        value={endpointSettings.lmstudio_model}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, lmstudio_model: e.target.value })}
                        placeholder="LM Studio model"
                      />
                      <Input
                        value={endpointSettings.deepseek_base_url}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, deepseek_base_url: e.target.value })}
                        placeholder="DeepSeek base URL"
                      />
                      <Input
                        value={endpointSettings.deepseek_model}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, deepseek_model: e.target.value })}
                        placeholder="DeepSeek model"
                      />
                      <Input
                        value={endpointSettings.google_base_url}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, google_base_url: e.target.value })}
                        placeholder="Google base URL"
                      />
                      <Input
                        value={endpointSettings.google_model}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, google_model: e.target.value })}
                        placeholder="Google model"
                      />
                      <Input
                        value={endpointSettings.chatglm_base_url}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, chatglm_base_url: e.target.value })}
                        placeholder="ChatGLM base URL"
                      />
                      <Input
                        value={endpointSettings.chatglm_model}
                        onChange={(e) => setEndpointSettings({ ...endpointSettings, chatglm_model: e.target.value })}
                        placeholder="ChatGLM model"
                      />
                    </div>
                  </div>
                </div>

                {/* Save Button */}
                <div className="flex justify-end pt-4 border-t">
                  <Button onClick={handleSaveAPISettings} disabled={isLoading}>
                    <Save className="h-4 w-4 mr-2" />
                    {isLoading ? 'Saving...' : 'Save Settings'}
                  </Button>
                </div>
              </div>
            </Card>

            {/* Security Notice */}
            <Card className="border-blue-200 bg-blue-50/90 p-4 dark:border-blue-800 dark:bg-blue-950/30">
              <div className="flex gap-3">
                <AlertCircle className="h-5 w-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="text-sm">
                  <p className="font-semibold text-blue-900 dark:text-blue-100 mb-1">
                    Security Notice
                  </p>
                  <p className="text-blue-800 dark:text-blue-200">
                    Your API keys are encrypted and stored securely. They are only used for AI code review operations and are never shared with third parties. You can delete your keys at any time.
                  </p>
                </div>
              </div>
            </Card>
          </TabsContent>

          <TabsContent value="projects">
            <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
              <h3 className="text-lg font-semibold mb-4">Your Projects</h3>
              <p className="text-muted-foreground">
                Projects you're contributing to will appear here.
              </p>
            </Card>
          </TabsContent>

          <TabsContent value="achievements">
            <Card className="border-white/70 bg-white/80 p-6 dark:border-white/10 dark:bg-slate-950/60">
              <h3 className="text-lg font-semibold mb-4">Achievements</h3>
              <p className="text-muted-foreground">
                Your achievements and badges will appear here.
              </p>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </MainLayout>
  );
}
