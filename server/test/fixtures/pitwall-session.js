// Synthetic, deterministic UI fixture. Never used by the production router.
export const session={session_key:999001,meeting_key:999001,session_name:'Race · TEST FIXTURE',session_type:'Race',location:'Silverstone',country_name:'United Kingdom',date_start:'2025-07-06T14:00:00Z',date_end:'2025-07-06T16:00:00Z',year:2025};
const drivers=[{driver_number:4,name_acronym:'NOR',full_name:'Lando Norris',team_name:'McLaren',team_colour:'FF8000'},{driver_number:81,name_acronym:'PIA',full_name:'Oscar Piastri',team_name:'McLaren',team_colour:'FF8000'},{driver_number:44,name_acronym:'HAM',full_name:'Lewis Hamilton',team_name:'Ferrari',team_colour:'E80020'}];
const withSession=row=>({...row,session_key:999001,meeting_key:999001});
export function fixture(topic,query){
 const feeds={sessions:[session],meetings:[{...session,meeting_name:'British Grand Prix · TEST FIXTURE'}],drivers,
 laps:drivers.flatMap((d,i)=>Array.from({length:5},(_,n)=>({...d,lap_number:n+1,date_start:new Date(Date.parse(session.date_start)+n*92000).toISOString(),lap_duration:91+i*.6+n*.05,duration_sector_1:29.1,duration_sector_2:32.7,duration_sector_3:29.2}))),
 position:drivers.map((d,i)=>({...d,position:i+1,date:'2025-07-06T14:08:00Z'})),
 intervals:drivers.map((d,i)=>({...d,gap_to_leader:i*2.13,interval:i?2.13:0,date:'2025-07-06T14:08:00Z'})),
 stints:drivers.map(d=>({...d,stint_number:1,lap_start:1,lap_end:5,compound:'MEDIUM',tyre_age_at_start:0})),
 pit:[{driver_number:44,lap_number:5,lane_duration:24.51,stop_duration:2.4,date:'2025-07-06T14:08:00Z'}],
 weather:[{date:'2025-07-06T14:08:00Z',air_temperature:21.4,track_temperature:34.2,humidity:62,wind_speed:3.1,wind_direction:215,pressure:1012,rainfall:0}],
 race_control:[{date:'2025-07-06T14:00:00Z',category:'Flag',flag:'GREEN',message:'TEST FIXTURE — green flag. Synthetic data for interface verification.'}],
 overtakes:[{date:'2025-07-06T14:02:00Z',overtaking_driver_number:4,overtaken_driver_number:81,position:1}],
 team_radio:[],starting_grid:drivers.map((d,i)=>({...d,position:i+1,lap_duration:87+i*.2})),session_result:drivers.map((d,i)=>({...d,position:i+1,number_of_laps:5,duration:460+i,gap_to_leader:i,dnf:false,dns:false,dsq:false})),
 championship_drivers:drivers.map((d,i)=>({...d,points_current:200-i*20,points_start:175-i*20,position_current:i+1,position_start:i+1})),championship_teams:[{team_name:'McLaren',position_current:1,position_start:1,points_current:380,points_start:337}]};
 if(['car_data','location'].includes(topic))return Array.from({length:180},(_,i)=>withSession({driver_number:Number(query.driver_number??4),date:new Date(Date.parse(query['date>'])+i*500).toISOString(),speed:180+90*Math.sin(i/15),throttle:Math.round(55+45*Math.sin(i/15)),brake:i%35<5?100:0,rpm:9000+i*10,n_gear:6,drs:0,x:Math.round(Math.cos(i/29)*1000),y:Math.round(Math.sin(i/29)*700),z:15}));
 return (feeds[topic]??[]).map(withSession);
}
