import React, { useState, useEffect } from 'react';
import './App.css';

interface Restaurant {
  name: string;
  city: string;
  location: string;
  cuisine: string;
  cost_for_two: number | null;
  rating: number | null;
  votes: number | null;
}

interface Recommendation {
  rank: number;
  restaurant: Restaurant;
  explanation: string;
}

interface RecommendationResponse {
  status: string;
  summary: string | null;
  recommendations: Recommendation[];
  message: string | null;
  warnings: string[];
  metadata: Record<string, any>;
}

interface FilterResponse {
  status: string;
  locations: string[];
  cuisines: string[];
}

function App() {
  // Filters data loaded from API
  const [locations, setLocations] = useState<string[]>([]);
  const [cuisines, setCuisines] = useState<string[]>([]);
  const [filtersLoading, setFiltersLoading] = useState<boolean>(true);
  const [filtersError, setFiltersError] = useState<string | null>(null);

  // User input preferences
  const [selectedLocation, setSelectedLocation] = useState<string>('');
  const [selectedCuisine, setSelectedCuisine] = useState<string>('Any');
  const [selectedBudget, setSelectedBudget] = useState<'low' | 'medium' | 'high'>('medium');
  const [minRating, setMinRating] = useState<number>(4.0);

  // Search execution states
  const [loading, setLoading] = useState<boolean>(false);
  const [results, setResults] = useState<RecommendationResponse | null>(null);
  const [hasSearched, setHasSearched] = useState<boolean>(false);

  // Load locations and cuisines on mount
  useEffect(() => {
    async function loadFilters() {
      try {
        const res = await fetch('/api/filters');
        if (!res.ok) {
          throw new Error(`Failed to load filters: ${res.statusText}`);
        }
        const data: FilterResponse = await res.json();
        setLocations(data.locations);
        setCuisines(data.cuisines);
        
        // Set default values
        if (data.locations.length > 0) {
          // Default to Indiranagar if present, else first location
          const defaultLoc = data.locations.includes('Indiranagar') ? 'Indiranagar' : data.locations[0];
          setSelectedLocation(defaultLoc);
        }
        setFiltersLoading(false);
      } catch (err: any) {
        console.error(err);
        setFiltersError(err.message || 'Could not connect to BiteAI backend.');
        setFiltersLoading(false);
      }
    }
    loadFilters();
  }, []);

  // Handle recommendation search
  const handleDiscover = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedLocation) return;

    setLoading(true);
    setResults(null);
    setHasSearched(true);

    try {
      const res = await fetch('/api/recommend', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          location: selectedLocation,
          budget: selectedBudget,
          cuisine: selectedCuisine,
          min_rating: minRating,
          additional_preferences: null, // AI directives removed as requested
        }),
      });

      if (!res.ok) {
        throw new Error(`Server returned error: ${res.status} ${res.statusText}`);
      }

      const data: RecommendationResponse = await res.json();
      setResults(data);
    } catch (err: any) {
      console.error(err);
      setResults({
        status: 'error',
        summary: null,
        recommendations: [],
        message: err.message || 'Failed to generate recommendations. Please try again.',
        warnings: [],
        metadata: { error_type: 'FrontendFetchException' }
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-surface-container-lowest text-on-surface font-body flex flex-col">
      {/* Top Header Bar */}
      <header className="sticky top-0 w-full z-50 flex items-center px-6 md:px-10 h-16 bg-surface-container-lowest/60 backdrop-blur-md border-b border-outline-variant/20 shadow-sm">
        <span className="font-display text-2xl md:text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary-container to-secondary-container">
          BiteAI
        </span>
      </header>

      <div className="flex flex-1 relative">
        {/* Left Sidebar Filter Panel */}
        <aside className="w-full md:w-80 flex flex-col p-6 border-r border-outline-variant/10 bg-surface-container-low/40 backdrop-blur-xl shrink-0">
          {/* Profile Header */}
          <div className="flex items-center gap-3 mb-6 p-2 rounded-xl bg-surface-container/30 border border-outline-variant/5">
            <div className="w-10 h-10 rounded-full overflow-hidden bg-primary-container/20 flex items-center justify-center border border-primary-container/30">
              <img 
                alt="BiteAI Concierge" 
                className="w-full h-full object-cover" 
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuBijgmeBhOIuGHCOBqe_ZatPVnGEBO2_cV0Pcgw6dAIN1Cs4JW_294yA5o-xnK1kuyw9-ZvQlCetiMfS3gRo-q5VYXSoo1LCkDTI9vOjNuQtbdgddZ8co9CsdxgqY5gHv513K4gwSxkDRi-1gsi0U7ejwdZ_TcKf9rHpa94uEwDtnkXkXw5LvKmzVj-ea__nvJAzZEWSQM72MfOhESr8EB7SmnKAbf0Rt8FpWI2wkGTfTMgKPSP_judzH9X9Mo2H4WaCy0Nk58VhwQ"
              />
            </div>
            <div>
              <h3 className="font-display text-[15px] font-semibold text-on-surface leading-tight">BiteAI Concierge</h3>
              <p className="font-body text-xs text-primary-brand font-medium">Premium Access</p>
            </div>
          </div>

          <h2 className="font-display text-lg font-bold text-white mb-4 flex items-center gap-2">
            <span>🍽️</span> Preference Panel
          </h2>

          {filtersLoading ? (
            <div className="flex flex-col gap-4 py-8 items-center text-on-surface-variant/60">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-primary-container border-r-2 border-r-transparent"></div>
              <span className="text-xs">Loading database filters...</span>
            </div>
          ) : filtersError ? (
            <div className="p-4 rounded-xl border border-red-500/20 bg-red-500/5 text-red-300 text-sm">
              <p className="font-bold mb-1">Database Error</p>
              <p>{filtersError}</p>
            </div>
          ) : (
            <form onSubmit={handleDiscover} className="flex flex-col gap-5 flex-1">
              {/* Location Select */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-on-surface/80">
                  Area / Neighborhood (Bangalore)
                </label>
                <div className="relative">
                  <select
                    className="w-full bg-surface-container-low border border-outline/20 rounded-lg py-2 px-3 text-sm text-on-surface focus:outline-none focus:border-primary-container focus:ring-1 focus:ring-primary-container appearance-none cursor-pointer"
                    value={selectedLocation}
                    onChange={(e) => setSelectedLocation(e.target.value)}
                  >
                    {locations.map((loc) => (
                      <option key={loc} value={loc} className="bg-surface-dim">
                        {loc}
                      </option>
                    ))}
                  </select>
                  <span className="material-symbols-outlined pointer-events-none absolute right-2.5 top-2.5 text-on-surface/50 text-sm">
                    arrow_drop_down
                  </span>
                </div>
              </div>

              {/* Cuisine Select */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-on-surface/80">
                  Cuisine Type
                </label>
                <div className="relative">
                  <select
                    className="w-full bg-surface-container-low border border-outline/20 rounded-lg py-2 px-3 text-sm text-on-surface focus:outline-none focus:border-primary-container focus:ring-1 focus:ring-primary-container appearance-none cursor-pointer"
                    value={selectedCuisine}
                    onChange={(e) => setSelectedCuisine(e.target.value)}
                  >
                    {cuisines.map((c) => (
                      <option key={c} value={c} className="bg-surface-dim">
                        {c}
                      </option>
                    ))}
                  </select>
                  <span className="material-symbols-outlined pointer-events-none absolute right-2.5 top-2.5 text-on-surface/50 text-sm">
                    arrow_drop_down
                  </span>
                </div>
              </div>

              {/* Budget Limit Select */}
              <div className="flex flex-col gap-1.5">
                <label className="text-xs font-bold uppercase tracking-wider text-on-surface/80">
                  Budget Limit
                </label>
                <div className="flex flex-col gap-2">
                  {[
                    { key: 'low', label: 'Low (under ₹500)' },
                    { key: 'medium', label: 'Medium (₹500 - ₹1500)' },
                    { key: 'high', label: 'High (above ₹1500)' },
                  ].map((option) => (
                    <label
                      key={option.key}
                      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border text-sm cursor-pointer transition-all ${
                        selectedBudget === option.key
                          ? 'border-primary-container bg-primary-container/5 text-white font-semibold shadow-sm'
                          : 'border-outline/10 hover:bg-surface-container/20 text-on-surface/70'
                      }`}
                    >
                      <input
                        type="radio"
                        name="budget"
                        className="accent-primary-container h-4 w-4"
                        checked={selectedBudget === option.key}
                        onChange={() => setSelectedBudget(option.key as any)}
                      />
                      <span>{option.label}</span>
                    </label>
                  ))}
                </div>
              </div>

              {/* Min Rating Slider */}
              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold uppercase tracking-wider text-on-surface/80">
                    Minimum Rating
                  </label>
                  <span className="text-sm font-semibold text-secondary-container bg-secondary-container/10 px-2 py-0.5 rounded-full border border-secondary-container/20">
                    ⭐ {minRating.toFixed(1)}
                  </span>
                </div>
                <input
                  type="range"
                  min="0.0"
                  max="5.0"
                  step="0.1"
                  className="w-full accent-primary-container h-1 bg-surface-container rounded-lg appearance-none cursor-pointer"
                  value={minRating}
                  onChange={(e) => setMinRating(parseFloat(e.target.value))}
                />
                <div className="flex justify-between text-[10px] text-on-surface-variant/40 px-0.5">
                  <span>0.0</span>
                  <span>2.5</span>
                  <span>5.0</span>
                </div>
              </div>

              <div className="mt-auto pt-4">
                <button
                  type="submit"
                  disabled={loading}
                  className={`w-full py-3.5 rounded-full bg-gradient-to-r from-primary-container to-secondary-container text-white font-display text-sm font-bold shadow-lg shadow-primary-container/15 hover:brightness-110 active:scale-98 transition-all cursor-pointer flex items-center justify-center gap-2 ${
                    loading ? 'opacity-80 cursor-not-allowed' : ''
                  }`}
                >
                  {loading ? (
                    <>
                      <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                      <span>Consulting AI Concierge...</span>
                    </>
                  ) : (
                    <>
                      <span>✨ Discover Restaurants</span>
                    </>
                  )}
                </button>
              </div>
            </form>
          )}
        </aside>

        {/* Main Content Area */}
        <main className="flex-1 px-6 md:px-10 py-6 overflow-y-auto max-h-[calc(100vh-4rem)]">
          {/* Main Title Banner */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8 border-b border-outline-variant/10 pb-6">
            <div>
              <span className="font-display text-3xl md:text-4xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary-container to-secondary-container">
                BiteAI recommendation
              </span>
              <p className="text-on-surface-variant/60 text-sm mt-1 max-w-2xl leading-relaxed">
                Culinary intelligence agent combining structured Zomato metadata and Groq Llama ranking.
              </p>
            </div>
            {hasSearched && !loading && (
              <div className="flex items-center gap-2">
                <button className="p-2.5 rounded-full glass hover:bg-surface-container-high transition-colors cursor-pointer text-on-surface/85">
                  <span className="material-symbols-outlined text-[20px]">share</span>
                </button>
                <button className="p-2.5 rounded-full glass hover:bg-surface-container-high transition-colors cursor-pointer text-on-surface/85">
                  <span className="material-symbols-outlined text-[20px]">filter_list</span>
                </button>
              </div>
            )}
          </div>

          {/* Feed States */}
          {loading ? (
            /* Loading State Skeleton */
            <div className="flex flex-col gap-6">
              <div className="h-28 rounded-2xl bg-surface-container/20 animate-pulse border border-outline-variant/5"></div>
              <div className="space-y-6">
                {[1, 2, 3].map((i) => (
                  <div key={i} className="glass rounded-2xl p-6 space-y-4 animate-pulse">
                    <div className="flex justify-between">
                      <div className="h-6 w-1/3 bg-surface-container-highest rounded"></div>
                      <div className="h-6 w-20 bg-surface-container-highest rounded"></div>
                    </div>
                    <div className="h-4 w-2/3 bg-surface-container-highest rounded"></div>
                    <div className="h-16 bg-surface-container-low/60 rounded"></div>
                  </div>
                ))}
              </div>
            </div>
          ) : results ? (
            /* Results Received */
            <div>
              {results.status === 'empty' ? (
                /* Empty Matches State — Intelligent Diagnostics */
                (() => {
                  const meta = results.metadata || {};
                  const filters = (meta.filters_applied || {}) as Record<string, any>;
                  const afterLoc = meta.after_location as number | undefined;
                  const afterCuisine = meta.after_cuisine as number | undefined;
                  const afterRating = meta.after_rating as number | undefined;
                  const afterBudget = meta.after_budget as number | undefined;
                  const loc = filters.location || selectedLocation;
                  const cuisine = filters.cuisine || selectedCuisine;
                  const budget = filters.budget || selectedBudget;
                  const rating = filters.min_rating ?? minRating;

                  // Determine the root cause
                  let icon = '📍';
                  let title = 'No Restaurants Found';
                  let explanation = '';
                  const suggestions: string[] = [];

                  if (afterLoc !== undefined && afterLoc === 0) {
                    // Location itself has no restaurants
                    icon = '🗺️';
                    title = `No Restaurants in ${loc}`;
                    explanation = `We don't have any restaurant data for "${loc}" in our Zomato database. This location may not be covered in our current Bangalore dataset.`;
                    suggestions.push('Try a nearby popular area like Indiranagar, Koramangala, or Whitefield.');
                    suggestions.push('Double-check the location spelling or select from the dropdown.');
                  } else if (afterCuisine !== undefined && afterCuisine === 0) {
                    // Location exists but cuisine not available there
                    icon = '🍽️';
                    title = `No ${cuisine} Restaurants in ${loc}`;
                    explanation = `We found ${afterLoc} restaurant${afterLoc !== 1 ? 's' : ''} in ${loc}, but none of them serve ${cuisine} cuisine. This cuisine type may not be available in this neighborhood.`;
                    suggestions.push(`Set Cuisine Type to "Any" to see all ${afterLoc} restaurants in ${loc}.`);
                    suggestions.push(`Try nearby locations that may have ${cuisine} restaurants.`);
                  } else if (afterRating !== undefined && afterRating === 0) {
                    // Cuisine exists in location but none meet the rating threshold
                    icon = '⭐';
                    title = 'Rating Too High for This Combination';
                    explanation = `We found ${afterCuisine} ${cuisine !== 'any' && cuisine !== 'Any' ? cuisine + ' ' : ''}restaurant${afterCuisine !== 1 ? 's' : ''} in ${loc}, but none have a rating of ${Number(rating).toFixed(1)} or above.`;
                    suggestions.push(`Lower your minimum rating to 3.5 or below — the available restaurants here may be rated slightly lower.`);
                    suggestions.push(`Check nearby areas like Koramangala or Indiranagar for higher-rated ${cuisine !== 'any' && cuisine !== 'Any' ? cuisine + ' ' : ''}options.`);
                  } else if (afterBudget !== undefined && afterBudget === 0) {
                    // Restaurants exist after location+cuisine+rating but not in budget
                    icon = '💰';
                    title = 'No Restaurants in This Budget Range';
                    const budgetLabel = budget === 'low' ? 'under ₹500' : budget === 'medium' ? '₹500–₹1500' : 'above ₹1500';
                    explanation = `We found ${afterRating} ${cuisine !== 'any' && cuisine !== 'Any' ? cuisine + ' ' : ''}restaurant${afterRating !== 1 ? 's' : ''} in ${loc} rated ${Number(rating).toFixed(1)}+, but none fall in the "${budgetLabel}" budget range.`;
                    suggestions.push(`Try a different budget level — the matching restaurants may be in a ${budget === 'low' ? 'higher' : 'different'} price bracket.`);
                    suggestions.push(`Lower your minimum rating to expand the pool of candidates within your budget.`);
                  } else {
                    // Generic fallback
                    explanation = results.message || 'No venues in our Zomato dataset match your current filter combination.';
                    suggestions.push('Lower your minimum rating filter (e.g. to 3.5 or 3.0).');
                    suggestions.push('Change Cuisine Type to "Any" to expand the candidate pool.');
                    suggestions.push('Try a different budget level.');
                  }

                  return (
                    <div className="glass border border-primary-container/30 rounded-2xl p-8 max-w-2xl mx-auto shadow-lg shadow-primary-container/5 my-8">
                      <div className="text-center">
                        <span className="text-5xl">{icon}</span>
                        <h3 className="text-primary-brand text-xl font-display font-semibold mt-4 mb-2">
                          {title}
                        </h3>
                        <p className="text-on-surface-variant/80 text-sm mb-6 leading-relaxed max-w-lg mx-auto">
                          {explanation}
                        </p>
                      </div>

                      {/* Filter Pipeline Breakdown */}
                      {afterLoc !== undefined && (
                        <div className="mb-6 p-4 rounded-xl bg-surface-container/30 border border-outline-variant/10">
                          <p className="text-xs font-bold uppercase tracking-wider text-on-surface/60 mb-3 flex items-center gap-1.5">
                            <span className="material-symbols-outlined text-sm">filter_alt</span>
                            Filter Pipeline Breakdown
                          </p>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                            {[
                              { label: 'Location', value: afterLoc, color: afterLoc > 0 ? 'text-green-400' : 'text-red-400' },
                              { label: 'Cuisine', value: afterCuisine, color: afterCuisine !== undefined && afterCuisine > 0 ? 'text-green-400' : 'text-red-400' },
                              { label: 'Rating', value: afterRating, color: afterRating !== undefined && afterRating > 0 ? 'text-green-400' : 'text-red-400' },
                              { label: 'Budget', value: afterBudget, color: afterBudget !== undefined && afterBudget > 0 ? 'text-green-400' : 'text-red-400' },
                            ].map((step) => (
                              <div key={step.label} className="text-center p-2 rounded-lg bg-surface-container-low/50">
                                <p className="text-[10px] uppercase tracking-wider text-on-surface-variant/50 mb-1">{step.label}</p>
                                <p className={`text-lg font-bold font-display ${step.color}`}>
                                  {step.value !== undefined ? step.value : '—'}
                                </p>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Actionable Suggestions */}
                      <hr className="border-t border-primary-container/10 my-4" />
                      <p className="text-xs font-bold uppercase tracking-wider text-white mb-3 flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-sm text-secondary-container">tips_and_updates</span>
                        What you can try
                      </p>
                      <ul className="text-on-surface-variant/70 text-sm list-none space-y-2.5 leading-relaxed">
                        {suggestions.map((s, i) => (
                          <li key={i} className="flex items-start gap-2">
                            <span className="text-secondary-container mt-0.5">→</span>
                            <span>{s}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  );
                })()
              ) : results.status === 'error' ? (
                /* Failure Error State */
                <div className="glass border border-red-500/30 bg-red-500/5 rounded-2xl p-8 max-w-2xl mx-auto text-center my-8">
                  <span className="text-4xl">🔥</span>
                  <h3 className="text-red-300 text-xl font-display font-semibold mt-4 mb-2">
                    AI Recommendation Failure
                  </h3>
                  <p className="text-on-surface/90 text-sm leading-relaxed">
                    {results.message || 'An unexpected error occurred during recommendation orchestration.'}
                  </p>
                </div>
              ) : (
                /* Success Layout Feed */
                <div className="space-y-8">
                  {/* Results Count Badge */}
                  <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-primary-container/10 border border-primary-container/20 text-primary-brand text-xs font-bold uppercase tracking-wider">
                    <span className="material-symbols-outlined text-[16px] material-fill">verified</span>
                    ⭐ Selected {results.recommendations.length} restaurants from {results.metadata.after_budget || results.recommendations.length} matches!
                  </div>

                  {/* AI Insight Summary Card */}
                  {results.summary && (
                    <section className="ai-summary-glow rounded-2xl bg-gradient-to-br from-[#2a1b3d] to-[#121725] border border-primary-container/25 p-8 relative overflow-hidden group">
                      <div className="absolute top-0 right-0 p-12 bg-primary-container/10 blur-[100px] rounded-full"></div>
                      <div className="relative z-10">
                        <div className="flex items-center gap-3 mb-4">
                          <span className="material-symbols-outlined text-tertiary-fixed-dim text-2xl">lightbulb</span>
                          <h2 className="font-display text-xl font-semibold text-tertiary-fixed-dim">
                            AI Insight Summary
                          </h2>
                        </div>
                        <p className="font-body text-sm md:text-base text-on-surface-variant leading-relaxed max-w-4xl">
                          {results.summary}
                        </p>
                      </div>
                    </section>
                  )}

                  {/* Recommendations Cards Feed */}
                  <div className="space-y-6">
                    {results.recommendations.map((rec) => {
                      const rest = rec.restaurant;
                      const ratingVal = rest.rating !== null ? rest.rating.toFixed(1) : '—';
                      const costVal = rest.cost_for_two ? `₹${rest.cost_for_two} for two` : 'Price not available';

                      return (
                        <div 
                          key={rec.rank} 
                          className="glass rounded-2xl p-6 md:p-8 hover:-translate-y-1 transition-all duration-300 group border border-outline-variant/10 shadow-md relative"
                        >
                          {/* Header section of Card */}
                          <div className="flex justify-between items-start flex-wrap gap-4 mb-4">
                            <div>
                              <h3 className="font-display text-xl md:text-2xl font-bold text-white flex items-center gap-3 flex-wrap">
                                <span>#{rec.rank} {rest.name}</span>
                                <span className="bg-secondary-container/15 text-secondary-container border border-secondary-container/25 rounded-full px-2.5 py-0.5 text-sm font-bold flex items-center gap-1">
                                  <span className="material-symbols-outlined text-xs material-fill">star</span>
                                  {ratingVal}
                                </span>
                              </h3>
                            </div>
                            <span className="text-primary-brand text-[10px] font-bold tracking-wider uppercase bg-primary-container/10 border border-primary-container/20 px-3 py-1 rounded-full">
                              Curated Pick
                            </span>
                          </div>

                          {/* Metadata row */}
                          <div className="flex flex-wrap gap-x-6 gap-y-3 text-xs md:text-sm text-on-surface-variant/80 font-body mb-6 border-b border-outline-variant/5 pb-4">
                            <div className="flex items-center gap-1.5">
                              <span className="text-[14px]">🍲</span>
                              <span><b>Cuisine:</b> {rest.cuisine}</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span className="text-[14px]">📍</span>
                              <span><b>Location:</b> {rest.location}, {rest.city}</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                              <span className="text-[14px]">💵</span>
                              <span><b>Estimated Cost:</b> {costVal}</span>
                            </div>
                          </div>

                          {/* AI Rationale box */}
                          <div className="bg-primary-container/3 border border-primary-container/10 rounded-xl p-5">
                            <div className="flex items-center gap-2 mb-2">
                              <span className="material-symbols-outlined text-primary-container text-lg">magic_button</span>
                              <span className="font-display text-xs font-bold text-primary-container tracking-wider uppercase">
                                AI Recommendation Rationale
                              </span>
                            </div>
                            <p className="font-body text-[14px] md:text-[15px] italic text-on-surface/90 leading-relaxed">
                              "{rec.explanation}"
                            </p>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          ) : (
            /* Default Welcome State */
            <div className="glass border-2 border-dashed border-outline/10 rounded-2xl p-12 text-center max-w-xl mx-auto my-12 bg-surface-container/5">
              <span className="text-5xl">🥘</span>
              <h3 className="text-white font-display text-xl font-semibold mt-4 mb-2">
                Ready to Explore?
              </h3>
              <p className="text-on-surface-variant/60 text-sm max-w-md mx-auto leading-relaxed">
                Adjust the filters in the left preference panel and click <b>Discover Restaurants</b> to run the AI concierge.
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

export default App;
