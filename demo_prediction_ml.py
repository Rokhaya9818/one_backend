"""
Démonstration des modèles ARIMA et Prophet avec données synthétiques
Ce script simule 60 jours de données FVR pour montrer comment les modèles
fonctionneront quand nous aurons suffisamment de données réelles.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif
import matplotlib.pyplot as plt
from prediction_advanced import LinearExtrapolation, ARIMAModel, ProphetModel, EnsembleModel

# Génère des données synthétiques réalistes
def generate_synthetic_fvr_data(days=60, base_cases=10, trend=0.5, noise_level=0.2):
    """
    Génère des données FVR synthétiques avec:
    - Tendance croissante (épidémie)
    - Saisonnalité hebdomadaire (moins de cas le weekend)
    - Bruit aléatoire
    """
    start_date = datetime(2024, 10, 1)
    dates = [start_date + timedelta(days=i) for i in range(days)]
    
    cases = []
    for i, date in enumerate(dates):
        # Tendance exponentielle (épidémie)
        trend_value = base_cases * (1 + trend) ** (i / 10)
        
        # Saisonnalité hebdomadaire (moins de cas le weekend)
        day_of_week = date.weekday()
        seasonal_factor = 0.7 if day_of_week in [5, 6] else 1.0
        
        # Bruit aléatoire
        noise = np.random.normal(0, noise_level * trend_value)
        
        # Valeur finale (toujours positive)
        value = max(1, trend_value * seasonal_factor + noise)
        cases.append(int(value))
    
    df = pd.DataFrame({
        'ds': dates,
        'y': cases
    })
    
    return df

# Fonction principale de démonstration
def demo_ml_models():
    print("=" * 80)
    print("DÉMONSTRATION DES MODÈLES DE PRÉDICTION ML")
    print("=" * 80)
    print("\n📊 Génération de 60 jours de données synthétiques FVR...")
    
    # Génère les données
    df = generate_synthetic_fvr_data(days=60, base_cases=15, trend=0.8, noise_level=0.15)
    
    print(f"✅ {len(df)} points temporels générés")
    print(f"📅 Période: {df['ds'].min().strftime('%Y-%m-%d')} → {df['ds'].max().strftime('%Y-%m-%d')}")
    print(f"📈 Cas: {df['y'].min():.0f} → {df['y'].max():.0f}")
    print(f"📊 Moyenne: {df['y'].mean():.1f} cas/jour")
    
    # Sépare en train/test (50 jours train, 10 jours test)
    train_df = df.iloc[:50]
    test_df = df.iloc[50:]
    
    print(f"\n🔧 Entraînement sur {len(train_df)} jours")
    print(f"🧪 Test sur {len(test_df)} jours")
    
    # Crée et entraîne les modèles
    models = {
        'Linear': LinearExtrapolation(),
        'ARIMA': ARIMAModel(),
        'Prophet': ProphetModel()
    }
    
    results = {}
    
    for name, model in models.items():
        print(f"\n{'='*80}")
        print(f"🤖 Modèle: {name}")
        print(f"{'='*80}")
        
        try:
            if not model.can_train(len(train_df)):
                print(f"❌ Pas assez de données ({len(train_df)} < {model.min_data_points})")
                continue
                
            print(f"⏳ Entraînement en cours...")
            model.train(train_df)
            print(f"✅ Entraînement terminé")
            
            print(f"🔮 Génération de prédictions pour {len(test_df)} jours...")
            predictions = model.predict(len(test_df))
            
            # Calcule les métriques
            actual = test_df['y'].values
            predicted = predictions['yhat'].values
            
            mae = np.mean(np.abs(actual - predicted))
            rmse = np.sqrt(np.mean((actual - predicted) ** 2))
            mape = np.mean(np.abs((actual - predicted) / actual)) * 100
            
            print(f"\n📊 MÉTRIQUES DE PERFORMANCE:")
            print(f"   MAE (Mean Absolute Error):      {mae:.2f} cas")
            print(f"   RMSE (Root Mean Squared Error): {rmse:.2f} cas")
            print(f"   MAPE (Mean Absolute % Error):   {mape:.2f}%")
            
            results[name] = {
                'predictions': predictions,
                'mae': mae,
                'rmse': rmse,
                'mape': mape
            }
            
            # Affiche quelques prédictions
            print(f"\n🔮 PRÉDICTIONS (premiers 5 jours):")
            for i in range(min(5, len(predictions))):
                pred_date = predictions.iloc[i]['ds']
                pred_value = predictions.iloc[i]['yhat']
                actual_value = test_df.iloc[i]['y']
                error = abs(pred_value - actual_value)
                print(f"   {pred_date.strftime('%Y-%m-%d')}: Prédit={pred_value:.1f}, Réel={actual_value:.0f}, Erreur={error:.1f}")
                
        except Exception as e:
            print(f"❌ Erreur: {e}")
            import traceback
            traceback.print_exc()
    
    # Compare les modèles
    if results:
        print(f"\n{'='*80}")
        print("🏆 COMPARAISON DES MODÈLES")
        print(f"{'='*80}")
        
        best_model = min(results.items(), key=lambda x: x[1]['rmse'])
        
        print(f"\n{'Modèle':<15} {'MAE':<12} {'RMSE':<12} {'MAPE':<12}")
        print("-" * 55)
        for name, metrics in results.items():
            marker = "🏆" if name == best_model[0] else "  "
            print(f"{marker} {name:<13} {metrics['mae']:>8.2f}    {metrics['rmse']:>8.2f}    {metrics['mape']:>8.2f}%")
        
        print(f"\n✨ Meilleur modèle: {best_model[0]} (RMSE = {best_model[1]['rmse']:.2f})")
    
    # Génère un graphique
    print(f"\n📈 Génération du graphique de comparaison...")
    
    plt.figure(figsize=(15, 8))
    
    # Données réelles
    plt.plot(df['ds'], df['y'], 'ko-', label='Données réelles', linewidth=2, markersize=4)
    
    # Ligne de séparation train/test
    split_date = train_df['ds'].iloc[-1]
    plt.axvline(x=split_date, color='gray', linestyle='--', label='Séparation Train/Test', alpha=0.5)
    
    # Prédictions de chaque modèle
    colors = {'Linear': 'blue', 'ARIMA': 'red', 'Prophet': 'green'}
    for name, result in results.items():
        pred_df = result['predictions']
        plt.plot(pred_df['ds'], pred_df['yhat'], color=colors[name], 
                label=f'{name} (RMSE={result["rmse"]:.1f})', linewidth=2, alpha=0.7)
        
        # Intervalle de confiance
        plt.fill_between(pred_df['ds'], 
                        pred_df['yhat_lower'], 
                        pred_df['yhat_upper'],
                        color=colors[name], alpha=0.1)
    
    plt.xlabel('Date', fontsize=12)
    plt.ylabel('Nombre de cas FVR', fontsize=12)
    plt.title('Comparaison des Modèles de Prédiction FVR (Données Synthétiques)', fontsize=14, fontweight='bold')
    plt.legend(loc='upper left', fontsize=10)
    plt.grid(True, alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    output_path = '/home/ubuntu/demo_prediction_comparison.png'
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"✅ Graphique sauvegardé: {output_path}")
    
    # Ensemble model
    print(f"\n{'='*80}")
    print("🎯 MODÈLE ENSEMBLE (Combinaison de tous les modèles)")
    print(f"{'='*80}")
    
    ensemble = EnsembleModel()
    for name, model in models.items():
        if model.is_trained:
            # Poids inversement proportionnel au RMSE
            weight = 1.0 / results[name]['rmse'] if name in results else 1.0
            ensemble.add_model(model, weight=weight)
            print(f"✅ {name} ajouté avec poids {weight:.3f}")
    
    print(f"\n🔮 Génération des prédictions ensemble...")
    ensemble_pred = ensemble.predict(len(test_df))
    
    # Métriques ensemble
    actual = test_df['y'].values
    predicted = ensemble_pred['yhat'].values
    
    mae = np.mean(np.abs(actual - predicted))
    rmse = np.sqrt(np.mean((actual - predicted) ** 2))
    mape = np.mean(np.abs((actual - predicted) / actual)) * 100
    
    print(f"\n📊 MÉTRIQUES ENSEMBLE:")
    print(f"   MAE:  {mae:.2f} cas")
    print(f"   RMSE: {rmse:.2f} cas")
    print(f"   MAPE: {mape:.2f}%")
    
    print(f"\n{'='*80}")
    print("✅ DÉMONSTRATION TERMINÉE")
    print(f"{'='*80}")
    
    return results, ensemble_pred

if __name__ == "__main__":
    results, ensemble_pred = demo_ml_models()
