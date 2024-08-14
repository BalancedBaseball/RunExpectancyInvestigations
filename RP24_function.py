def compute_RP24(startyear = 2023, endyear = 2024, preregpost = 'reg'):
    
    import pandas as pd
    import numpy as np
    import pybaseball
    
    for year in range(startyear, endyear + 1):
        try:
            df_year = pd.read_csv('statcast{}.csv'.format(year))
        except FileNotFoundError:
            df_year = pybaseball.statcast(start_dt='{}-01-01'.format(year), end_dt='{}-12-31'.format(year))
            df_year.to_csv('statcast{}.csv'.format(year))
        if 'df_multiyear' in locals() or 'df_multiyear' in globals():
            df_multiyear = df_multiyear.append(df_year, ignore_index=True)
        else:
            df_multiyear = df_year
    
    df = df_multiyear
    
    try:
        df = df.drop('Unnamed: 0', axis = 1)
    except:
        pass
            
    if preregpost == 'reg':
        df = df[df['game_type'] == 'R']
    if preregpost == 'pre':
        df = df[(df['game_type'] == 'E') | (df['game_type'] == 'S')]
    if preregpost == 'post':
        df = df[(df['game_type'] == 'W') | (df['game_type'] == 'L') | (df['game_type'] == 'F') | (df['game_type'] == 'D')]
    if preregpost == 'prereg':
        df = df[(df['game_type'] == 'R') | (df['game_type'] == 'E') | (df['game_type'] == 'S')]
    if preregpost == 'prepost':
        df = df[(df['game_type'] == 'E') | (df['game_type'] == 'S') | (df['game_type'] == 'W') | (df['game_type'] == 'L') | (df['game_type'] == 'F') | (df['game_type'] == 'D')]
    if preregpost == 'regpost':
        df = df[(df['game_type'] == 'R') | (df['game_type'] == 'W') | (df['game_type'] == 'L') | (df['game_type'] == 'F') | (df['game_type'] == 'D')]
    if preregpost == 'all':
        pass
    
    
    df['half_inning_id'] = df['game_pk'].astype(str) + df['inning'].astype(str) + df['inning_topbot'].astype(str)
    
    df['runs_scored_on_play'] = df['post_bat_score'] - df['bat_score']
    
    RunsOnPlay = df[['half_inning_id', 'bat_score', 'post_bat_score', 'runs_scored_on_play']]
    RunsOnPlay = RunsOnPlay.rename(columns = {'bat_score': 'runs_before_inning', 'post_bat_score': 'runs_after_inning',
                                                 'runs_scored_on_play': 'runs_scored_in_inning'})

    RunsBeforeInning = RunsOnPlay[['half_inning_id', 'runs_before_inning']].groupby(['half_inning_id']).min()
    RunsScoredDuringInning = RunsOnPlay[['half_inning_id', 'runs_scored_in_inning']].groupby(['half_inning_id']).sum()
    RunsAfterInning = RunsOnPlay[['half_inning_id', 'runs_after_inning']].groupby(['half_inning_id']).max()

    RunsInInning = RunsBeforeInning.join(RunsScoredDuringInning, how = 'left').join(RunsAfterInning, how = 'left')
    
    inning_startend = df[['game_pk', 'half_inning_id', 'inning_topbot', 'at_bat_number', 'pitch_number', 'events',
                          'bat_score', 'post_bat_score', 'post_away_score', 'post_home_score']]
    inning_startend['ab_id'] = inning_startend['half_inning_id'].astype(str) + inning_startend['at_bat_number'].astype(str)
    last_ab = inning_startend.loc[inning_startend.groupby(['game_pk'])['at_bat_number'].idxmax()]
    last_pitch_of_ab = inning_startend.loc[inning_startend.groupby(['ab_id'])['pitch_number'].idxmax()]
    last_pitch_of_game = pd.merge(last_ab, last_pitch_of_ab, how = 'inner')
    
    confirmed_walkoffs = last_pitch_of_game[(last_pitch_of_game['post_away_score'] < last_pitch_of_game['post_home_score']) & 
                                        (last_pitch_of_game['inning_topbot'] == 'Bot')]
    
    RunsInInning = RunsInInning.reset_index()
    RunsInInning = RunsInInning[~RunsInInning['half_inning_id'].isin(confirmed_walkoffs['half_inning_id'])]
    
    df = df.set_index(['half_inning_id']).join(RunsInInning.set_index(['half_inning_id']), how = 'left')
    df['runs_rest_of_inning'] = df['runs_after_inning'] - df['bat_score']
    
    ## FIRST MAJOR CHANGE:
    ## For run probability (i.e. the probability of scoring a run during or after a given scenario)
    ## we will add a new column that is a binary as to whether a run is scored after that scenario
    ## takes place
    df['score_in_inning_binary'] = np.where(df['runs_rest_of_inning'] > 0, 1, 0)
    
    df['1B_binary'] = np.where(df['on_1b'].notna(), 1, 0)
    df['2B_binary'] = np.where(df['on_2b'].notna(), 1, 0)
    df['3B_binary'] = np.where(df['on_3b'].notna(), 1, 0)
    df['state'] = ("Bases: " + df['1B_binary'].astype(str) + df['2B_binary'].astype(str) + 
                   df['3B_binary'].astype(str) + ", Outs: " + df['outs_when_up'].astype(str))
    
    df = df.reset_index()
    df['ab_id'] = df['half_inning_id'].astype(str) + df['at_bat_number'].astype(str)
    df['pitch_id'] = df['half_inning_id'].astype(str) + df['at_bat_number'].astype(str) + df['pitch_number'].astype(str)
    
    ## SECOND MAJOR CHANGE
    ## Make sure to include this when we subset for this dataframe
    RunsExpectancyData = df[['half_inning_id', 'ab_id', 'pitch_id', 'pitch_number', '1B_binary', '2B_binary', '3B_binary', 'outs_when_up',  'des', 
                         'runs_scored_on_play', 'runs_before_inning', 'runs_scored_in_inning',
                         'runs_after_inning', 'runs_rest_of_inning', 'score_in_inning_binary', 'state']]
    
    abs_with_changes = RunsExpectancyData[['ab_id', 'pitch_id', 'pitch_number', 'des', 'state', 'runs_scored_on_play']]
    abs_with_changes = abs_with_changes.sort_values(['pitch_id', 'state', 'runs_scored_on_play'], ascending = False)
    abs_with_changes = abs_with_changes.drop_duplicates(subset = ['ab_id', 'state'], keep = 'first')
    
    RE24_data_year = RunsExpectancyData[RunsExpectancyData['pitch_id'].isin(abs_with_changes['pitch_id'])][['outs_when_up', '1B_binary', '2B_binary', '3B_binary', 'score_in_inning_binary']]
    RE24_data_year['Bases'] = RE24_data_year['1B_binary'].astype(str) + RE24_data_year['2B_binary'].astype(str) + RE24_data_year['3B_binary'].astype(str)
    RE24_data_year = RE24_data_year.drop(columns = ['1B_binary', '2B_binary', '3B_binary'])
    
    ## Minor change: replacing the name of the column
    RE24_data_year = RE24_data_year.rename(columns = {'outs_when_up': 'Outs', 'score_in_inning_binary': 'Runs'})
    RE24_data_year = RE24_data_year.groupby(['Bases', 'Outs']).mean()
    RE24_data_year = RE24_data_year.reset_index()
    
    RE24_year = RE24_data_year.pivot(index='Bases', columns='Outs', values='Runs')
    
    return RE24_year