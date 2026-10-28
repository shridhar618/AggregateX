"""Character Lab control contract and concise relative prompt vocabulary.
Shared Text fields use the same attribute keys, avoiding conflicting duplicate values.
"""
def slider(key,label,low,high):
    return {'key':key,'label':label,'kind':'slider','low':low,'high':high}
def choice(key,label,options,shared=False):
    return {'key':key,'label':label,'kind':'select','options':options,'shared':shared}
def text(key,label):
    return {'key':key,'label':label,'kind':'text'}

GROUPS=[
 {'id':'face','label':'Structure & Shape','short':'Face','icon':'person','fields':[
  slider('face_width','Face width','narrow','broad'),slider('forehead_width','Forehead width','narrow','broad'),
  slider('cheekbone_height','Cheekbone height','low','high'),slider('cheek_fullness','Cheek fullness','lean','full'),
  slider('jaw_width','Jaw width','narrow','broad'),slider('chin_width','Chin width','narrow','broad'),
  slider('chin_length','Chin length','short','long'),choice('face_shape','Face shape',['Oval','Round','Square','Oblong','Heart','Diamond'])]},
 {'id':'eyes','label':'Eyes & Nose','short':'Eyes','icon':'eye','fields':[
  slider('eye_size','Eye size','small','large'),slider('eye_separation','Eye separation','close-set','wide-set'),
  slider('eye_height','Eye height','low-set','high-set'),choice('eye_shape','Eye shape',['Almond','Round','Hooded','Deep-set','Upturned','Downturned']),
  choice('eyes','Eye color',['Brown','Blue','Green','Hazel','Gray'],True),slider('eyebrow_thickness','Eyebrow thickness','thin','thick'),
  slider('nose_size','Nose size','small','large'),slider('nose_width','Nose width','narrow','broad'),slider('nose_length','Nose length','short','long'),
  choice('nose_bridge','Nose bridge',['Straight','Convex','Concave','Low','High'])]},
 {'id':'mouth','label':'Mouth & Jaw','short':'Mouth','icon':'emoji-neutral','fields':[
  slider('lip_fullness','Lip fullness','thin','full'),slider('mouth_width','Mouth width','narrow','wide'),
  slider('jaw_angle','Jaw angle','soft','angular'),slider('chin_prominence','Chin prominence','recessed','prominent'),
  choice('expression','Expression',['Neutral','Relaxed','Serious','Slight smile'])]},
 {'id':'hair','label':'Hair Analysis','short':'Hair','icon':'scissors','fields':[
  text('hairstyle','Hairstyle'),choice('hair','Hair color',['Black','Brown','Blond','Red','Gray','White','No visible hair'],True),
  slider('hair_texture','Hair texture','straight','tightly curled'),slider('hairline','Hairline recession','full hairline','receded'),
  choice('facial-hair','Facial hair',['None','Stubble','Mustache','Beard','Goatee'],True),slider('beard_density','Beard density','sparse','dense')]},
 {'id':'build','label':'Physical Build','short':'Build','icon':'person-arms-up','fields':[
  slider('body_weight','Body weight appearance','lean','heavy-set'),slider('muscle_mass','Muscle appearance','slight','muscular'),
  slider('shoulder_width','Shoulder width','narrow','broad'),slider('neck_thickness','Neck thickness','slender','thick')]},
 {'id':'marks','label':'Distinguishing Details','short':'Marks','icon':'patch-exclamation','fields':[
  text('scar','Scar description / location'),choice('scar_side','Scar side (subject’s anatomical side)',['Left','Right','Midline']),
  text('moles','Moles / birthmarks and location'),text('tattoos','Visible tattoos and location'),text('other_marks','Other distinguishing marks'),
  choice('glasses','Glasses recalled',['None','Present','Uncertain'])]},
 {'id':'appearance','label':'Appearance & Presentation','short':'Look','icon':'palette','fields':[
  {'key':'age','label':'Estimated age appearance','kind':'age','shared':True},
  choice('complexion','Skin appearance / tone',['Fair','Light','Medium','Olive','Brown','Dark'],True),
  text('clothing','Clothing'),text('glasses_style','Glasses style'),text('headwear','Headwear'),
  choice('pose','Pose',['Front-facing','Three-quarter left','Three-quarter right','Profile left','Profile right'])]}
]
FIELDS={f['key']:f for group in GROUPS for f in group['fields']}
LAB_FIELDS={key:field for key,field in FIELDS.items() if not field.get('shared')}

def phrase(key,value):
    field=FIELDS.get(key)
    if not field or field['kind']!='slider':
        return value
    v=int(value)
    if 41<=v<=59:
        return 'neutral relative setting'
    if v<=40:
        return ('markedly ' if v<=20 else 'slightly ')+field['low']
    return ('markedly ' if v>=80 else 'slightly ')+field['high']
