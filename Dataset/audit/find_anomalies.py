import pandas as pd

df = pd.read_csv('Dataset/output/master_players.csv')

print(f"Total players: {len(df)}")

anomalies = []

# List of famous pure bowlers
famous_bowlers = [
    'Dale Steyn', 'Makhaya Ntini', 'Morne Morkel', 'Kagiso Rabada', 'Anrich Nortje',
    'Lasith Malinga', 'Muttiah Muralitharan', 'Dilhara Fernando', 'Suranga Lakmal',
    'Nuwan Kulasekara', 'Nuwan Pradeep', 'Rangana Herath',
    'Glenn McGrath', 'Shane Warne', 'Brett Lee', 'Mitchell Starc', 'Pat Cummins', 'Josh Hazlewood',
    'James Anderson', 'Stuart Broad', 'Jofra Archer', 'Mark Wood',
    'Jasprit Bumrah', 'Mohammed Shami', 'Zaheer Khan', 'Javagal Srinath', 'Bhuvneshwar Kumar', 'Anil Kumble', 'Harbhajan Singh',
    'Wasim Akram', 'Waqar Younis', 'Shoaib Akhtar', 'Shaheen Shah Afridi', 'Saqlain Mushtaq',
    'Trent Boult', 'Tim Southee', 'Shane Bond', 'Lockie Ferguson',
    'Courtney Walsh', 'Curtly Ambrose', 'Ian Bishop', 'Kemar Roach', 'Shannon Gabriel',
    'Mashrafe Mortaza', 'Mustafizur Rahman', 'Taskin Ahmed',
    'Rashid Khan', 'Mujeeb Ur Rahman', 'Fazalhaq Farooqi', 'Naveen-ul-Haq'
]

# List of famous pure batsmen
famous_batsmen = [
    'Virat Kohli', 'Rohit Sharma', 'Sachin Tendulkar', 'Rahul Dravid', 'VVS Laxman', 'Virender Sehwag', 'Cheteshwar Pujara', 'Ajinkya Rahane', 'Shubman Gill', 'Yashasvi Jaiswal',
    'Ricky Ponting', 'Steve Waugh', 'Mark Waugh', 'Matthew Hayden', 'Justin Langer', 'David Warner', 'Steve Smith', 'Marnus Labuschagne', 'Travis Head', 'Michael Clarke', 'Damien Martyn',
    'Joe Root', 'Alastair Cook', 'Kevin Pietersen', 'Michael Vaughan', 'Graham Gooch', 'David Gower', 'Ian Bell', 'Zak Crawley', 'Ollie Pope', 'Harry Brook',
    'Babar Azam', 'Inzamam-ul-Haq', 'Younis Khan', 'Mohammad Yousuf', 'Saeed Anwar', 'Javed Miandad', 'Zaheer Abbas', 'Saleem Malik', 'Fakhar Zaman',
    'Kane Williamson', 'Martin Guptill', 'Ross Taylor', 'Stephen Fleming', 'Nathan Astle', 'Brendon McCullum', 'Devon Conway',
    'Brian Lara', 'Vivian Richards', 'Shivnarine Chanderpaul', 'Chris Gayle', 'Desmond Haynes', 'Gordon Greenidge', 'Ramnaresh Sarwan', 'Shimron Hetmyer', 'Shai Hope',
    'Graeme Smith', 'Hashim Amla', 'Gary Kirsten', 'Daryll Cullinan', 'Faf du Plessis', 'Dean Elgar', 'Aiden Markram', 'Temba Bavuma', 'David Miller', 'Ashwell Prince',
    'Mahela Jayawardene', 'Marvan Atapattu', 'Aravinda de Silva', 'Sanath Jayasuriya', 'Tillakaratne Dilshan', 'Dimuth Karunaratne', 'Pathum Nissanka', 'Charith Asalanka',
    'Tamim Iqbal', 'Najmul Hossain Shanto', 'Mominul Haque', 'Habibul Bashar'
]

# List of famous wicketkeepers
famous_wks = [
    'MS Dhoni', 'Rishabh Pant', 'Dinesh Karthik', 'Nayan Mongia', 'Wriddhiman Saha', 'KL Rahul',
    'Adam Gilchrist', 'Brad Haddin', 'Ian Healy', 'Rod Marsh', 'Alex Carey', 'Matthew Wade',
    'Kumar Sangakkara', 'Romesh Kaluwitharana', 'Dinesh Chandimal', 'Kusal Perera', 'Niroshan Dickwella',
    'Mark Boucher', 'Quinton de Kock', 'Heinrich Klaasen', 'Dave Richardson', 'Kyle Verreynne',
    'Brendon McCullum', 'BJ Watling', 'Tom Blundell', 'Luke Ronchi', 'Tom Latham',
    'Alec Stewart', 'Matt Prior', 'Jonny Bairstow', 'Jos Buttler', 'Jack Russell', 'Geraint Jones', 'Ben Foakes',
    'Kamran Akmal', 'Moin Khan', 'Rashid Latif', 'Sarfaraz Ahmed', 'Mohammad Rizwan',
    'Ridley Jacobs', 'Denesh Ramdin', 'Nicholas Pooran', 'Shai Hope', 'Jeff Dujon', 'Junior Murray',
    'Mushfiqur Rahim', 'Khaled Mashud', 'Litton Das',
    'Andy Flower', 'Tatenda Taibu', 'Brendan Taylor',
    'Mohammad Shahzad', 'Rahmanullah Gurbaz'
]

for idx, r in df.iterrows():
    name = r['player_name']
    country = r['country']
    dec = r['decade']
    role = r['primary_role']
    wk = r['is_wicketkeeper']
    bat_r = r['batting_rating']
    bowl_r = r['bowling_rating']
    pos = str(r['eligible_positions'])
    
    # Check if a famous bowler is marked as BAT or has batting > 70
    if name in famous_bowlers and role == 'BAT':
        anomalies.append(f"Row {r['player_id']} | {name} ({country} {dec}): Famous Bowler is marked as BAT (bat={bat_r}, bowl={bowl_r})")
    elif name in famous_bowlers and role not in ('PACE', 'SPIN', 'AR'):
        anomalies.append(f"Row {r['player_id']} | {name} ({country} {dec}): Famous Bowler role is {role}")
        
    # Check if famous batsman is marked as PACE or SPIN
    if name in famous_batsmen and role in ('PACE', 'SPIN'):
        anomalies.append(f"Row {r['player_id']} | {name} ({country} {dec}): Famous Batsman marked as {role} (bat={bat_r}, bowl={bowl_r})")
        
    # Check if famous wicketkeeper is marked as PACE or SPIN
    if name in famous_wks and role in ('PACE', 'SPIN'):
        anomalies.append(f"Row {r['player_id']} | {name} ({country} {dec}): Famous Wicketkeeper marked as {role}")
        
    # Check if a non-wicketkeeper has wk=True
    if wk and name not in famous_wks and name not in ['AB de Villiers', 'Kumar Sangakkara']:
        anomalies.append(f"Row {r['player_id']} | {name} ({country} {dec}): is_wicketkeeper is True but player is not in known keeper list")
        
    # Check if wicketkeeper has wk=False
    if name in famous_wks and not wk and name not in ['Rahul Dravid']:
        anomalies.append(f"Row {r['player_id']} | {name} ({country} {dec}): is_wicketkeeper is False for known keeper")

print(f"\nFound {len(anomalies)} obvious role/player anomalies:")
for a in anomalies:
    print(" ", a)
