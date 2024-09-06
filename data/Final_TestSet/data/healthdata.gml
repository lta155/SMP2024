graph [
  node [
    id 0
    label "1"
    name "Community A"
    health_indicator 75
  ]
  node [
    id 1
    label "2"
    name "Community B"
    health_indicator 60
  ]
  node [
    id 2
    label "3"
    name "Community C"
    health_indicator 85
  ]
  node [
    id 3
    label "4"
    name "Community D"
    health_indicator 50
  ]
  edge [
    source 0
    target 1
    weight 1.5
  ]
  edge [
    source 0
    target 2
    weight 2.0
  ]
  edge [
    source 1
    target 3
    weight 1.0
  ]
  edge [
    source 2
    target 3
    weight 2.5
  ]
]
